import os
import time
from typing import Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Minimal CrowdStrike OAuth2 client and helpers to get new-detections count.
# Secrets via env: CS_CLIENT_ID, CS_CLIENT_SECRET

class CrowdStrikeAuthError(Exception):
    pass

class CrowdStrikeClient:
    def __init__(self, base_url: str = "https://api.crowdstrike.com"):
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "ey-cs-monitor/0.1"})

    def _get_client_creds(self):
        cid = os.getenv("CS_CLIENT_ID")
        csecret = os.getenv("CS_CLIENT_SECRET")
        if not cid or not csecret:
            raise CrowdStrikeAuthError("CS_CLIENT_ID/CS_CLIENT_SECRET not set")
        return cid, csecret

    def _auth_headers(self):
        if not self._token or time.time() > self._token_expiry - 60:
            self._refresh_token()
        return {"Authorization": f"Bearer {self._token}"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8),
           retry=retry_if_exception_type(requests.RequestException))
    def _refresh_token(self):
        cid, csecret = self._get_client_creds()
        url = f"{self.base_url}/oauth2/token"
        resp = self._session.post(url, data={
            "client_id": cid,
            "client_secret": csecret
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        self._token = data.get("access_token")
        expires_in = int(data.get("expires_in", 1700))
        self._token_expiry = time.time() + expires_in

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8),
           retry=retry_if_exception_type(requests.RequestException))
    def get_new_detections_count(self) -> int:
        """
        Polling fallback: approximate "New detections" via detections within a recent window.
        This can be tailored; here we use detections within the last hour as a proxy count.
        """
        url = f"{self.base_url}/detects/queries/detects/v1"
        headers = self._auth_headers()
        # Filter: last 60 minutes
        filter_q = "last_behavior -24h"  # loosen to day; dashboard's 'new' may be session-based
        params = {"filter": filter_q}
        resp = self._session.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        resources = resp.json().get("resources", [])
        return len(resources)

    def stream_events(self):
        """
        Placeholder for streaming via Falcon SIEM Connector or Event Streams.
        In production, subscribe to the relevant event stream (detections) and yield events.
        This function is defined to allow an event-driven mode without polling.
        """
        raise NotImplementedError("Streaming not implemented in this sample. Use mode=poll.")
