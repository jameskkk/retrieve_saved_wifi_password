from typing import List

from .base import Backend
from .command import run
from ..errors import NetworkNotFoundError, PermissionDeniedError, WifiPasswordError
from ..models import SavedNetwork


def _split_escaped(value: str, separator: str = ":") -> List[str]:
    """Split nmcli's terse output while honoring backslash escapes."""

    fields: List[str] = []
    current: List[str] = []
    escaped = False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == separator:
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    fields.append("".join(current))
    return fields


class NetworkManagerBackend(Backend):
    """Read Ubuntu Wi-Fi profiles through NetworkManager's nmcli."""

    def _profiles(self) -> List[SavedNetwork]:
        output = run(["nmcli", "-t", "-f", "NAME,UUID,TYPE", "connection", "show"])
        profiles: List[SavedNetwork] = []
        for line in output.splitlines():
            fields = _split_escaped(line)
            if len(fields) == 3 and fields[2] in {"802-11-wireless", "wifi"}:
                name, uuid, _ = fields
                profiles.append(SavedNetwork(ssid=name, profile_id=uuid))
        return profiles

    def _secrets(self, profile: SavedNetwork) -> SavedNetwork:
        try:
            output = run(
                [
                    "nmcli",
                    "--show-secrets",
                    "--escape",
                    "no",
                    "-g",
                    "802-11-wireless.ssid,802-11-wireless-security.psk",
                    "connection",
                    "show",
                    "uuid",
                    profile.profile_id or "",
                ]
            )
        except WifiPasswordError as exc:
            message = str(exc)
            if "permission" in message.lower() or "not authorized" in message.lower():
                raise PermissionDeniedError(
                    "NetworkManager denied access; retry with an account allowed to read system connections"
                ) from exc
            raise

        values = output.splitlines()
        ssid = values[0] if values and values[0] else profile.ssid
        password = values[1] if len(values) > 1 and values[1] else None
        return SavedNetwork(
            ssid=ssid,
            password=password,
            profile_id=profile.profile_id,
            error=None if password else "No PSK is stored (the network may be open or use enterprise authentication)",
        )

    def list_networks(self, include_passwords: bool = False) -> List[SavedNetwork]:
        profiles = self._profiles()
        if not include_passwords:
            return profiles

        resolved = []
        for profile in profiles:
            try:
                resolved.append(self._secrets(profile))
            except WifiPasswordError as exc:
                resolved.append(
                    SavedNetwork(
                        ssid=profile.ssid,
                        profile_id=profile.profile_id,
                        error=str(exc),
                    )
                )
        return resolved

    def get_network(self, ssid: str) -> SavedNetwork:
        profiles = self._profiles()
        # Connection names usually equal SSIDs. Prefer an exact name first so a
        # lookup does not request secrets for unrelated profiles.
        for profile in profiles:
            if profile.ssid == ssid:
                return self._secrets(profile)
        for profile in profiles:
            resolved = self._secrets(profile)
            if resolved.ssid == ssid:
                return resolved
        raise NetworkNotFoundError(f"No saved Wi-Fi network named {ssid!r} was found")
