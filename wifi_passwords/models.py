from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SavedNetwork:
    """A saved Wi-Fi profile and, when requested, its credential."""

    ssid: str
    password: Optional[str] = None
    profile_id: Optional[str] = None
    interface: Optional[str] = None
    error: Optional[str] = None
