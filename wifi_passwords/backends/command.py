import subprocess
from typing import Sequence

from ..errors import ToolNotFoundError, WifiPasswordError


def run(command: Sequence[str]) -> str:
    """Run an OS utility without invoking a shell."""

    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise ToolNotFoundError(f"Required command {command[0]!r} was not found") from exc

    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise WifiPasswordError(detail or f"{command[0]} exited with status {result.returncode}")
    return result.stdout
