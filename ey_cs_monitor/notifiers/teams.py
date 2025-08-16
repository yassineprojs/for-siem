import os
import json
import requests
from typing import List, Dict
from .base import Notifier

class TeamsNotifier(Notifier):
    def __init__(self, webhook_env: str):
        self.webhook_env = webhook_env

    def send(self, title: str, message: str, link: str | None, recipients: List[str], silent: bool = False) -> Dict:
        webhook = os.getenv(self.webhook_env)
        if not webhook:
            return {"ok": False, "error": f"Missing env {self.webhook_env}"}
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": title,
            "themeColor": "0076D7",
            "title": title,
            "text": message + (f"\n[Open in CrowdStrike]({link})" if link else ""),
        }
        resp = requests.post(webhook, data=json.dumps(card), headers={"Content-Type": "application/json"}, timeout=10)
        ok = resp.status_code in (200, 204)
        return {"ok": ok, "status": resp.status_code, "body": resp.text[:200]}
