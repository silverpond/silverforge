"""
Slot manager for concurrent port allocation.

Each worker has a fixed pool of N slots. A slot maps to a unique port
(slot_port_base + slot_index). Runs that need a port acquire a slot before
starting and release it when done.

All concurrent runs live in one Python process (ThreadPoolExecutor), so a
threading.Lock is sufficient — no filesystem locking needed.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Dict, Generator, Tuple

if TYPE_CHECKING:
    from factory.ssh import SSHClient


class SlotManager:
    def __init__(self, n_slots: int, port_base: int):
        self._lock = threading.Lock()
        self._available = list(range(1, n_slots + 1))  # slots numbered 1..N
        self._port_base = port_base

    def port_for(self, slot: int) -> int:
        return self._port_base + slot

    @contextmanager
    def acquire(self, poll_interval: int = 10) -> Generator[Tuple[int, int], None, None]:
        """Block until a slot is free, yield (slot, port), then release."""
        slot = self._acquire_slot(poll_interval)
        try:
            yield slot, self.port_for(slot)
        finally:
            self._release_slot(slot)

    def _acquire_slot(self, poll_interval: int) -> int:
        while True:
            with self._lock:
                if self._available:
                    return self._available.pop(0)
            time.sleep(poll_interval)

    def _release_slot(self, slot: int) -> None:
        with self._lock:
            self._available.append(slot)


def teardown_port(client: "SSHClient", port: int) -> None:
    """
    Kill any processes listening on port via SIGTERM then SIGKILL.

    Mirrors the teardown_slot_services pattern from the highlighter factory:
    agents may start detached services that survive tmux kill-session, keeping
    the port bound and blocking slot reuse.
    """
    if port <= 0:
        return
    script = (
        f"for sig in TERM KILL; do "
        f"  pids=$(ss -tlnpH 'sport = :{port}' 2>/dev/null "
        f"    | grep -oE 'pid=[0-9]+' | sed 's/pid=//' | sort -u || true); "
        f"  [ -z \"$pids\" ] && break; "
        f"  for pid in $pids; do kill -$sig $pid 2>/dev/null || true; done; "
        f"  [ \"$sig\" = TERM ] && sleep 2; "
        f"done"
    )
    client.run(script, timeout=15)


# Module-level registry: one SlotManager per worker name.
_managers: Dict[str, SlotManager] = {}
_registry_lock = threading.Lock()


def get_manager(worker_name: str, n_slots: int, port_base: int) -> SlotManager:
    """Return (or create) the SlotManager for a given worker."""
    with _registry_lock:
        if worker_name not in _managers:
            _managers[worker_name] = SlotManager(n_slots, port_base)
        return _managers[worker_name]
