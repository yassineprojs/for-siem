import os
from typing import List, Dict
import requests
from .base import Notifier

class TwilioSMSNotifier(Notifier):
    def __init__(self, account_sid_env: str = "TWILIO_ACCOUNT_SID", auth_token_env: str = "TWILIO_AUTH_TOKEN", from_env: str = "TWILIO_FROM"):
        self.account_sid_env = account_sid_env
        self.auth_token_env = auth_token_env
        self.from_env = from_env

    def send(self, title: str, message: str, link: str | None, recipients: List[str], silent: bool = False) -> Dict:
        sid = os.getenv(self.account_sid_env)
        token = os.getenv(self.auth_token_env)
        from_num = os.getenv(self.from_env)
        if not (sid and token and from_num):
            return {"ok": False, "error": "Missing TWILIO envs"}
        text = f"{title}: {message}"
        if link:
            text += f" {link}"
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        ok_all = True
        reports = []
        for to in recipients:
            data = {"To": to, "From": from_num, "Body": text}
            resp = requests.post(url, data=data, auth=(sid, token), timeout=10)
            ok = 200 <= resp.status_code < 300
            ok_all = ok_all and ok
            reports.append({"to": to, "status": resp.status_code})
        return {"ok": ok_all, "reports": reports}
