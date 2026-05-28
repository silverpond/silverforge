"""
SSH helpers using subprocess.

Keeps things simple: no paramiko, no asyncio, just ssh(1).
BatchMode=yes means it will fail cleanly if keys aren't set up.

When the target host is the local machine, commands run via subprocess
directly — no SSH needed.
"""
from __future__ import annotations

import os
import socket
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SSHResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def _is_local(host: str) -> bool:
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        local = socket.gethostname()
        if host == local or host == socket.getfqdn(local) or host == socket.getfqdn():
            return True
        # Fall back to comparing resolved IPs
        return socket.gethostbyname(host) == socket.gethostbyname(local)
    except OSError:
        return False


class SSHClient:
    def __init__(self, host: str, user: str, port: int = 22, identity_file: Optional[str] = None, shell_init: Optional[str] = None):
        self.host = host
        self.user = user
        self.port = port
        self.identity_file = identity_file
        self.shell_init = shell_init  # prepended to every command, e.g. "source /etc/profile"
        self.local = _is_local(host)

    def _base_args(self) -> List[str]:
        args = [
            "ssh",
            "-p", str(self.port),
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=accept-new",
        ]
        if self.identity_file:
            args += ["-i", os.path.expanduser(self.identity_file)]
        args.append(f"{self.user}@{self.host}")
        return args

    def run(self, command: str, timeout: Optional[int] = 60) -> SSHResult:
        """Run a single shell command — locally if host is this machine, otherwise over SSH."""
        if self.shell_init:
            command = f"{self.shell_init} && {command}"
        if self.local:
            cmd_args = ["bash", "-c", command]
        else:
            cmd_args = self._base_args() + [command]
        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return SSHResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            return SSHResult(exit_code=-1, stdout="", stderr=f"Command timed out after {timeout}s")
        except FileNotFoundError:
            return SSHResult(exit_code=-1, stdout="", stderr="ssh not found on PATH")

    def ping(self) -> bool:
        """Return True if we can reach the host and run a basic command."""
        result = self.run("echo pong", timeout=10)
        return result.ok and "pong" in result.stdout
