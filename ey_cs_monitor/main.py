import argparse
import json
import signal
import time
from datetime import datetime, time as dtime
from pathlib import Path

from .cs_client import CrowdStrikeClient
from .config_schema import AppConfig
from .logger_setup import setup_logger
from .notifiers.slack import SlackNotifier
from .notifiers.teams import TeamsNotifier
from .notifiers.sms import TwilioSMSNotifier
from .notifiers.pushover import PushoverNotifier

RUNNING = True

def within_quiet_hours(qh_start: str, qh_end: str) -> bool:
    now = datetime.now().time()
    s = dtime.fromisoformat(qh_start)
    e = dtime.fromisoformat(qh_end)
    if s <= e:
        return s <= now <= e
    else:
        return now >= s or now <= e


def load_config(path: str) -> AppConfig:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)


def build_notifiers(cfg: AppConfig):
    notifiers = []
    if cfg.notifiers.slack.enabled:
        notifiers.append(("slack", SlackNotifier(cfg.notifiers.slack.channel_webhook_env or "SLACK_WEBHOOK_URL"), cfg.notifiers.slack.recipients))
    if cfg.notifiers.teams.enabled:
        notifiers.append(("teams", TeamsNotifier(cfg.notifiers.teams.channel_webhook_env or "TEAMS_WEBHOOK_URL"), cfg.notifiers.teams.recipients))
    if cfg.notifiers.sms.enabled:
        notifiers.append(("sms", TwilioSMSNotifier(from_env=cfg.notifiers.sms.twilio_from_env or "TWILIO_FROM"), cfg.notifiers.sms.recipients))
    if cfg.notifiers.pushover.enabled:
        notifiers.append(("pushover", PushoverNotifier(), cfg.notifiers.pushover.recipients))
    return notifiers


def notify_all(notifiers, title: str, message: str, link: str | None, silent: bool, logger, suppress_sms_in_quiet: bool = True):
    reports = []
    for name, notifier, recipients in notifiers:
        if silent and suppress_sms_in_quiet and name == "sms":
            reports.append({"channel": name, "ok": True, "skipped": "quiet_hours"})
            continue
        try:
            r = notifier.send(title, message, link, recipients, silent=silent)
        except Exception as e:
            r = {"ok": False, "error": str(e)}
        reports.append({"channel": name, **r})
    logger.info("notification_sent", extra={"extra": {"reports": reports}})


def graceful_shutdown(*_):
    global RUNNING
    RUNNING = False


def cli():
    parser = argparse.ArgumentParser(description="EY CrowdStrike New Detections Monitor")
    parser.add_argument("--config", default="./config.yaml")
    parser.add_argument("--once", action="store_true", help="Run one iteration then exit (for testing)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    logger = setup_logger(cfg.log_path)
    logger.info("starting", extra={"extra": {"mode": cfg.mode}})

    signal.signal(signal.SIGINT, graceful_shutdown)
    try:
        signal.signal(signal.SIGTERM, graceful_shutdown)
    except Exception:
        pass

    cs = CrowdStrikeClient(base_url=cfg.cs_base_url)

    last_count_path = Path(".build/last_count.json")
    last_count_path.parent.mkdir(exist_ok=True)
    if last_count_path.exists():
        try:
            last = json.loads(last_count_path.read_text())
            last_count = int(last.get("count", 0))
        except Exception:
            last_count = 0
    else:
        last_count = 0

    notifiers = build_notifiers(cfg)

    def handle_count(curr_count: int):
        nonlocal last_count
        if curr_count > last_count:
            title = f"New CrowdStrike detections: {curr_count}"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = f"Increase from {last_count} to {curr_count} at {ts}."
            link = cfg.new_detections_url
            silent = within_quiet_hours(cfg.quiet_hours.start, cfg.quiet_hours.end)
            notify_all(notifiers, title, msg, link, silent, logger, suppress_sms_in_quiet=cfg.suppress_sms_in_quiet_hours)
            last_count = curr_count
            last_count_path.write_text(json.dumps({"count": last_count, "ts": ts}))
            logger.info("state_updated", extra={"extra": {"count": last_count}})

    if cfg.mode == "stream":
        try:
            for evt in cs.stream_detection_events():
                # Increment count on each detection event and trigger notification
                try:
                    severity = (evt.get("event") or {}).get("Severity", "")
                    curr = last_count + 1
                    # Temporarily modify quiet-hours behavior if critical
                    if severity in (cfg.critical_severities or []):
                        title = f"CRITICAL CrowdStrike detection (count -> {curr})"
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        msg = f"Critical severity event at {ts}. Count increased to {curr}."
                        link = cfg.new_detections_url
                        notify_all(notifiers, title, msg, link, False, logger, suppress_sms_in_quiet=False)
                        last_count = curr
                        last_count_path.write_text(json.dumps({"count": last_count, "ts": ts}))
                        logger.info("state_updated", extra={"extra": {"count": last_count}})
                    else:
                        handle_count(curr)
                except Exception as e:
                    logger.error(f"stream_handle_error: {e}")
                if args.once:
                    break
        except Exception as e:
            logger.error(f"stream_error_fallback_to_poll: {e}")
            cfg.mode = "poll"

    if cfg.mode == "poll":
        while RUNNING:
            try:
                count = cs.get_new_detections_count()
                handle_count(count)
            except Exception as e:
                logger.error(f"poll_error: {e}")
            if args.once:
                break
            time.sleep(max(10, cfg.poll_interval_seconds))
    else:
        logger.error("unknown_mode")

if __name__ == "__main__":
    cli()
