import os
import time
from typing import Optional, Iterator, Tuple, Dict, Any
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
        url = f"{self.base_url}/detects/queries/detects/v1"
        headers = self._auth_headers()
        params = {"filter": "last_behavior -24h"}
        resp = self._session.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        resources = resp.json().get("resources", [])
        return len(resources)

    # --- Streaming (Event Streams v2) helpers ---
    def _open_datafeed(self, app_id: str = "ey-cs-monitor") -> Dict[str, Any]:
        """Request a datafeed (Event Streams v2). Returns a resource with URL and token."""
        url = f"{self.base_url}/sensors/entities/datafeed/v2"
        headers = self._auth_headers()
        params = {"appId": app_id}
        resp = self._session.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        resources = resp.json().get("resources", [])
        if not resources:
            raise RuntimeError("No datafeed resources available")
        # pick the first shard
        return resources[0]

    def _iter_sse(self, url: str, token: str) -> Iterator[Tuple[str, str]]:
        """Minimal SSE iterator. Yields (event, data_str). Tries common auth header patterns."""
        headers1 = {"Accept": "text/event-stream", "Authorization": f"Token {token}"}
        headers2 = {"Accept": "text/event-stream", "Authorization": f"Bearer {token}"}
        for headers in (headers1, headers2):
            try:
                with self._session.get(url, headers=headers, stream=True, timeout=90) as r:
                    r.raise_for_status()
                    event = "message"
                    data_lines = []
                    for line in r.iter_lines(decode_unicode=True):
                        if line is None:
                            continue
                        if line.startswith(":"):
                            # comment/keepalive
                            continue
                        if not line:
                            if data_lines:
                                yield event, "\n".join(data_lines)
                                data_lines = []
                                event = "message"
                            continue
                        if line.startswith("event:"):
                            event = line.split(":", 1)[1].strip()
                        elif line.startswith("data:"):
                            data_lines.append(line.split(":", 1)[1].lstrip())
            except requests.RequestException:
                # try next header style
                continue
            break

    def stream_detection_events(self, app_id: str = "ey-cs-monitor") -> Iterator[Dict[str, Any]]:
        """
        Connects to Falcon Event Streams and yields DetectionSummaryEvent payloads.
        Requires appropriate API scopes and that Event Streams is enabled for the tenant.
        """
        resource = self._open_datafeed(app_id)
        url = resource.get("url")
        token = resource.get("token")
        if not (url and token):
            raise RuntimeError("Invalid datafeed resource")
        for evt, data in self._iter_sse(url, token):
            if not data:
                continue
            try:
                obj = requests.utils.json.loads(data)
            except Exception:
                continue
            # Common envelope has metadata.eventType
            meta = obj.get("metadata") or obj.get("Metadata") or {}
            etype = meta.get("eventType") or meta.get("EventType")
            if etype == "DetectionSummaryEvent":
                yield obj
