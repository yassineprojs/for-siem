import os
import json
import requests
from typing import List, Dict
from .base import Notifier

class SlackNotifier(Notifier):
    def __init__(self, webhook_env: str):
        self.webhook_env = webhook_env

    def send(self, title: str, message: str, link: str | None, recipients: List[str], silent: bool = False) -> Dict:
        webhook = os.getenv(self.webhook_env)
        if not webhook:
            return {"ok": False, "error": f"Missing env {self.webhook_env}"}
        text = f"*{title}*\n{message}"
        if link:
            text += f"\n<{link}|Open in CrowdStrike>"
        payload = {"text": text}
        resp = requests.post(webhook, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=10)
        ok = resp.status_code in (200, 204)
        return {"ok": ok, "status": resp.status_code, "body": resp.text[:200]}
