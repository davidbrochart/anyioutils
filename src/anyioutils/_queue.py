from typing import Generic, TypeVar

from anyio import create_memory_object_stream


T = TypeVar("T")


class Queue(Generic[T]):
    def __init__(self, maxsize: int = 0):
        """
        A first in, first out (FIFO) queue.

        If *maxsize* is less than or equal to zero, the queue size is infinite. If it is an integer greater than `0`, then `await put()` blocks when the queue reaches *maxsize* until an item is removed by [get()][anyioutils.Queue.get].

        """
        self._maxsize = maxsize
        max_buffer_size = float("inf") if maxsize <= 0 else maxsize
        self._send_stream, self._receive_stream = create_memory_object_stream[T](max_buffer_size=max_buffer_size)

    @property
    def maxsize(self) -> int:
        """
        Number of items allowed in the queue.
        """
        return self._maxsize

    def qsize(self) -> int:
        """
        Returns:
            The number of items in the queue.
        """
        return self._send_stream.statistics().current_buffer_used

    def empty(self) -> bool:
        """
        Returns:
            `True` if the queue is empty, `False` otherwise.
        """
        return self._send_stream.statistics().current_buffer_used == 0

    def full(self) -> bool:
        """
        Returns:
            `True` if there are [maxsize][anyioutils.Queue.maxsize] items in the queue.
        """
        statistics = self._send_stream.statistics()
        return statistics.current_buffer_used == statistics.max_buffer_size

    async def put(self, item: T) -> None:
        """
        Put an item into the queue. If the queue is full, wait until a free slot is available before adding the item.

        Args:
            item: The item to put into the queue.
        """
        await self._send_stream.send(item)

    def put_nowait(self, item: T) -> None:
        """
        Put an item into the queue without blocking.

        Args:
            item: The item to put into the queue.
        """
        self._send_stream.send_nowait(item)

    async def get(self) -> T:
        """
        Remove and return an item from the queue. If queue is empty, wait until an item is available.

        Returns:
            The item from the queue.
        """
        return await self._receive_stream.receive()

    def get_nowait(self) -> T:
        """
        Returns:
            An item if one is immediately available.
        """
        return self._receive_stream.receive_nowait()

    def __del__(self) -> None:
        self._send_stream.close()
        self._receive_stream.close()
