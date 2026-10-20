import sys
from typing import Optional

from .base import Backend
from ..errors import UnsupportedPlatformError


def get_backend(platform: Optional[str] = None) -> Backend:
    """Return the backend for *platform* (or the current system)."""

    selected = (platform or sys.platform).lower()
    if selected in {"darwin", "mac", "macos"}:
        from .macos import MacOSBackend

        return MacOSBackend()
    if selected in {"linux", "ubuntu"}:
        from .linux import NetworkManagerBackend

        return NetworkManagerBackend()
    if selected in {"win32", "windows", "win"}:
        from .windows import WindowsBackend

        return WindowsBackend()
    raise UnsupportedPlatformError(
        f"Unsupported platform {selected!r}; supported systems are macOS, Ubuntu, and Windows"
    )


__all__ = ["Backend", "get_backend"]
