from typing import Generic, TypeVar

from anyio import create_memory_object_stream


T = TypeVar("T")


class Queue(Generic[T]):
    def __init__(self, maxsize: int = 0):
        self._maxsize = maxsize
        max_buffer_size = float("inf") if maxsize <= 0 else maxsize
        self._send_stream, self._receive_stream = create_memory_object_stream[T](max_buffer_size=max_buffer_size)

    @property
    def maxsize(self) -> int:
        return self._maxsize

    def qsize(self) -> int:
        return self._send_stream.statistics().current_buffer_used

    def empty(self) -> bool:
        return self._send_stream.statistics().current_buffer_used == 0

    def full(self) -> bool:
        statistics = self._send_stream.statistics()
        return statistics.current_buffer_used == statistics.max_buffer_size

    async def put(self, item: T) -> None:
        await self._send_stream.send(item)

    def put_nowait(self, item: T) -> None:
        self._send_stream.send_nowait(item)

    async def get(self) -> T:
        return await self._receive_stream.receive()

    def get_nowait(self) -> T:
        return self._receive_stream.receive_nowait()

    def __del__(self) -> None:
        self._send_stream.close()
        self._receive_stream.close()
