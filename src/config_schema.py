from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional

class QuietHours(BaseModel):
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")

class ChannelConfig(BaseModel):
    enabled: bool = False
    recipients: List[str] = []
    channel_webhook_env: Optional[str] = None
    twilio_from_env: Optional[str] = None

class NotifiersConfig(BaseModel):
    slack: ChannelConfig = ChannelConfig()
    teams: ChannelConfig = ChannelConfig()
    sms: ChannelConfig = ChannelConfig()
    pushover: ChannelConfig = ChannelConfig()

class AppConfig(BaseModel):
    mode: str = "stream"  # stream|poll
    poll_interval_seconds: int = 60
    cs_base_url: str = "https://api.crowdstrike.com"
    new_detections_url: Optional[str] = None
    quiet_hours: QuietHours = QuietHours(start="02:00", end="04:00")
    notifiers: NotifiersConfig = NotifiersConfig()
    log_path: str = "./logs/audit.log.jsonl"
