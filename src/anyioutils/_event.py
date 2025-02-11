from anyio import Event as _Event


class Event:
    def __init__(self) -> None:
        self._event = _Event()

    async def wait(self) -> bool:
        await self._event.wait()
        return True

    def set(self) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    def clear(self) -> None:
        if self._event.is_set():
            self._event = _Event()
