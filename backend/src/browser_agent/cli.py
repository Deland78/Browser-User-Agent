"""Developer convenience commands invoked via ``python -m`` or entry points."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run(module: str, *args: str) -> int:
    """Run a Python module as a subprocess and propagate the exit code."""
    command = [sys.executable, "-m", module, *args]
    process = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    return process.returncode


def lint() -> None:
    """Run Ruff lint checks."""
    sys.exit(_run("ruff", "check", "src"))


def format() -> None:
    """Apply Black formatting."""
    sys.exit(_run("black", "src"))


def typecheck() -> None:
    """Execute mypy static analysis."""
    sys.exit(_run("mypy", "src"))


def main() -> None:
    """Default command prints available sub-commands."""
    print(
        "Available commands:\n"
        "  browser-agent-lint      Run Ruff lint checks\n"
        "  browser-agent-format    Apply Black formatting\n"
        "  browser-agent-typecheck Run mypy static analysis"
    )


if __name__ == "__main__":
    main()
