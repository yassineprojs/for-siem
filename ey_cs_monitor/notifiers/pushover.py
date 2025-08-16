import os
from typing import List, Dict
import requests
from .base import Notifier

class PushoverNotifier(Notifier):
    def __init__(self, token_env: str = "PUSHOVER_TOKEN"):
        self.token_env = token_env

    def send(self, title: str, message: str, link: str | None, recipients: List[str], silent: bool = False) -> Dict:
        token = os.getenv(self.token_env)
        if not token:
            return {"ok": False, "error": f"Missing env {self.token_env}"}
        url = "https://api.pushover.net/1/messages.json"
        ok_all = True
        reports = []
        for user_env in recipients:
            user = os.getenv(user_env) if user_env.startswith("PUSHOVER_") else user_env
            data = {
                "token": token,
                "user": user,
                "title": title,
                "message": message + (f"\n{link}" if link else ""),
                "priority": 0 if silent else 1,
            }
            resp = requests.post(url, data=data, timeout=10)
            ok = 200 <= resp.status_code < 300
            ok_all &= ok
            reports.append({"user": user, "status": resp.status_code})
        return {"ok": ok_all, "reports": reports}
