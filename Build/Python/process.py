"""Run external commands with captured output and structured logging."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .constants import log


def run(cmd: list[str], *, cwd: Path | None = None, stage: str = "") -> None:
    """Run a subprocess, log command and stdout/stderr, exit the process on failure."""
    label = f"[{stage}] " if stage else ""
    log.info("%sRunning: %s", label, " ".join(str(c) for c in cmd))
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        for line in result.stdout.splitlines():
            log.info("%s  stdout: %s", label, line)
    if result.stderr:
        for line in result.stderr.splitlines():
            log.warning("%s  stderr: %s", label, line)
    if result.returncode != 0:
        log.error("%sCommand failed (exit %d): %s", label, result.returncode, " ".join(str(c) for c in cmd))
        combined = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        combined = combined.strip()
        if combined:
            tail = combined[-12000:] if len(combined) > 12000 else combined
            log.error("%s--- subprocess output (tail) ---\n%s", label, tail)
        sys.exit(1)
