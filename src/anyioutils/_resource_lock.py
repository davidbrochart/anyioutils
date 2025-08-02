from typing import Any

from anyio import Lock


class ResourceLock:
    """ResourceLock ensures that accesses cannot be done concurrently on the same resource."""

    _locks: dict[Any, Lock]

    def __init__(self):
        self._locks = {}

    def __call__(self, idx: Any):
        return _ResourceLock(idx, self._locks)


class _ResourceLock:
    _idx: Any
    _locks: dict[Any, Lock]
    _lock: Lock

    def __init__(self, idx: Any, locks: dict[Any, Lock]):
        self._idx = idx
        self._locks = locks

    async def __aenter__(self):
        if self._idx not in self._locks:
            self._locks[self._idx] = Lock()
        self._lock = self._locks[self._idx]
        await self._lock.acquire()

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        self._lock.release()
        if self._idx in self._locks:
            del self._locks[self._idx]
