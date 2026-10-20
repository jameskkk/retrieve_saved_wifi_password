import re
from typing import List

from .base import Backend
from .command import run
from ..errors import NetworkNotFoundError, PermissionDeniedError, WifiPasswordError
from ..models import SavedNetwork


class MacOSBackend(Backend):
    """Read preferred networks and passwords from macOS Keychain."""

    def _wifi_devices(self) -> List[str]:
        output = run(["networksetup", "-listallhardwareports"])
        devices: List[str] = []
        blocks = re.split(r"\n\s*\n", output.strip())
        for block in blocks:
            port = re.search(r"^Hardware Port:\s*(.+)$", block, re.MULTILINE)
            device = re.search(r"^Device:\s*(.+)$", block, re.MULTILINE)
            if port and device and port.group(1).strip() in {"Wi-Fi", "AirPort"}:
                devices.append(device.group(1).strip())
        return devices

    def _password(self, ssid: str) -> str:
        try:
            return run(
                [
                    "security",
                    "find-generic-password",
                    "-D",
                    "AirPort network password",
                    "-a",
                    ssid,
                    "-w",
                ]
            ).rstrip("\r\n")
        except WifiPasswordError as exc:
            message = str(exc)
            if "User interaction is not allowed" in message or "authorization" in message.lower():
                raise PermissionDeniedError(
                    "macOS Keychain denied access; allow access in the Keychain prompt and retry"
                ) from exc
            raise

    def list_networks(self, include_passwords: bool = False) -> List[SavedNetwork]:
        devices = self._wifi_devices()
        if not devices:
            raise WifiPasswordError("No Wi-Fi hardware interface was found")

        by_ssid = {}
        for device in devices:
            output = run(["networksetup", "-listpreferredwirelessnetworks", device])
            lines = output.splitlines()[1:]
            for line in lines:
                ssid = line.strip()
                if ssid and ssid not in by_ssid:
                    by_ssid[ssid] = SavedNetwork(ssid=ssid, interface=device)

        networks = list(by_ssid.values())
        if not include_passwords:
            return networks

        resolved = []
        for network in networks:
            try:
                resolved.append(
                    SavedNetwork(
                        ssid=network.ssid,
                        password=self._password(network.ssid),
                        interface=network.interface,
                    )
                )
            except WifiPasswordError as exc:
                resolved.append(
                    SavedNetwork(
                        ssid=network.ssid,
                        interface=network.interface,
                        error=str(exc),
                    )
                )
        return resolved

    def get_network(self, ssid: str) -> SavedNetwork:
        known = {network.ssid: network for network in self.list_networks()}
        if ssid not in known:
            raise NetworkNotFoundError(f"No saved Wi-Fi network named {ssid!r} was found")
        network = known[ssid]
        return SavedNetwork(
            ssid=ssid,
            password=self._password(ssid),
            interface=network.interface,
        )
