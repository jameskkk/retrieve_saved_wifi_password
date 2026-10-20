from abc import ABC, abstractmethod
from typing import List, Optional

from ..errors import NetworkNotFoundError
from ..models import SavedNetwork


class Backend(ABC):
    @abstractmethod
    def list_networks(self, include_passwords: bool = False) -> List[SavedNetwork]:
        """Return saved Wi-Fi profiles."""

    def get_network(self, ssid: str) -> SavedNetwork:
        """Return a saved network matching *ssid*, including its password."""

        matches = [
            network
            for network in self.list_networks(include_passwords=True)
            if network.ssid == ssid
        ]
        if not matches:
            raise NetworkNotFoundError(f"No saved Wi-Fi network named {ssid!r} was found")
        return matches[0]
