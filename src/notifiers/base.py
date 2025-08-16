from __future__ import annotations
from typing import List, Dict
from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    def send(self, title: str, message: str, link: str | None, recipients: List[str], silent: bool = False) -> Dict:
        ...
