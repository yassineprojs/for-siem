# EY CrowdStrike New Detections Monitor

A lightweight, secure tool that watches CrowdStrike's Activity Dashboard for increases in the "New detections" counter and notifies analysts via mobile-friendly channels (Slack/Teams/SMS/Pushover). Designed for SOC use with minimal footprint and safe defaults.

## Features

- Tracks "New detections" counter; alerts only on increments (state-change events).
- CrowdStrike Event Streams (preferred) or polling fallback via REST. No page scraping required.
- Pluggable notifiers: Slack, Teams, Twilio SMS, Pushover. Extend easily.
- Secure config: env vars for secrets; config file only for non-secrets.
- Local JSON audit log for every alert.
- Quiet hours support and per-channel subscribers.
- Runs as a Windows service (NSSM) or systemd on Linux; also Docker.

## Quick start

1. Create a Python 3.9+ virtual env and install:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e .
```

2. Copy the example config and edit:

```powershell
copy .\config.example.yaml .\config.yaml
```

3. Set secrets as environment variables (examples):

```powershell
$env:CS_CLIENT_ID = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:CS_CLIENT_SECRET = "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
# Optional notifiers
$env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/..."
$env:TEAMS_WEBHOOK_URL = "https://outlook.office.com/webhook/..."
$env:TWILIO_ACCOUNT_SID = "AC..."; $env:TWILIO_AUTH_TOKEN = "..."; $env:TWILIO_FROM = "+15551234567"
$env:PUSHOVER_TOKEN = "..."; $env:PUSHOVER_USER = "..."
```

4. Run the monitor:

```powershell
ey-cs-monitor --config .\config.yaml
```

### Docker

```powershell
# Build
docker build -t ey-cs-monitor .
# Run (pass secrets via env)
docker run --rm -e CS_CLIENT_ID -e CS_CLIENT_SECRET -e SLACK_WEBHOOK_URL -v ${PWD}:/app ey-cs-monitor --config /app/config.yaml
```

## Configuration (`config.yaml`)

- `mode`: `stream` (prefer) or `poll`.
- `poll_interval_seconds`: e.g., 60.
- `quiet_hours`: `{ start: "02:00", end: "04:00" }` (local time).
- `suppress_sms_in_quiet_hours`: true to deliver SMS only outside quiet hours (other channels deliver silently).
- `new_detections_url`: optional link for analysts.
- `notifiers`: enable and set per-channel recipients.

See `config.example.yaml` for a template.

## Run as a service

- Windows: use NSSM to wrap the command as a service so it runs in background on loginless hosts.
  - Path: `C:\\Python311\\Scripts\\ey-cs-monitor.exe` (or your venv path)
  - Arguments: `--config C:\\path\\to\\config.yaml`
  - Set environment variables in the NSSM GUI (or via system env).
- Linux: a sample `systemd` unit is included in `packaging/systemd/ey-cs-monitor.service`.

## Security notes

- Never commit secrets. Use env vars or a vault provider.
- HTTPS enforced for API endpoints.
- Logs contain only: timestamp, count, mode, recipients, and link.

## Development

```powershell
pip install -e .
pytest
```

## License

Internal EY use only.
