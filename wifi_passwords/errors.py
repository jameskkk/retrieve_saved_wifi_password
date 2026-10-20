class WifiPasswordError(RuntimeError):
    """Base error for expected credential lookup failures."""


class UnsupportedPlatformError(WifiPasswordError):
    """Raised when the current operating system has no backend."""


class ToolNotFoundError(WifiPasswordError):
    """Raised when an operating-system command is unavailable."""


class PermissionDeniedError(WifiPasswordError):
    """Raised when the OS refuses access to a stored credential."""


class NetworkNotFoundError(WifiPasswordError):
    """Raised when no saved profile matches the requested network."""
