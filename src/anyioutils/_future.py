from __future__ import annotations

from typing import Any, Callable

from anyio import Event, create_task_group
from anyio.abc import TaskGroup


class CancelledError(Exception):
    pass


class InvalidStateError(Exception):
    pass


class Future:
    _done_callbacks: list[Callable[[Future], None]]
    _exception: BaseException | None
    _task_group: TaskGroup

    def __init__(self) -> None:
        self._result_event = Event()
        self._exception_event = Event()
        self._cancelled_event = Event()
        self._done_callbacks = []
        self._done = False
        self._exception = None

    def _call_callbacks(self) -> None:
        for callback in self._done_callbacks:
            callback(self)

    async def _wait_result(self) -> None:
        await self._result_event.wait()
        self._task_group.cancel_scope.cancel()

    async def _wait_exception(self) -> None:
        await self._exception_event.wait()
        self._task_group.cancel_scope.cancel()

    async def _wait_cancelled(self) -> None:
        await self._cancelled_event.wait()
        self._task_group.cancel_scope.cancel()

    def cancel(self) -> None:
        self._done = True
        self._cancelled_event.set()
        self._call_callbacks()

    def cancelled(self) -> bool:
        return self._cancelled_event.is_set()

    async def wait(self) -> Any:
        if self._result_event.is_set():
            return self._result
        if self._exception_event.is_set():
            assert self._exception is not None
            raise self._exception
        if self._cancelled_event.is_set():
            raise CancelledError

        async with create_task_group() as self._task_group:
            self._task_group.start_soon(self._wait_result)
            self._task_group.start_soon(self._wait_exception)
            self._task_group.start_soon(self._wait_cancelled)

        if self._result_event.is_set():
            return self._result
        if self._exception_event.is_set():
            assert self._exception is not None
            raise self._exception
        if self._cancelled_event.is_set():
            raise CancelledError
        raise RuntimeError("Future has no result, no exception, and was not cancelled")  # pragma: no cover

    def done(self) -> bool:
        return self._done

    def set_result(self, value: Any) -> None:
        if self._done:
            raise InvalidStateError
        self._done = True
        self._result = value
        self._result_event.set()
        self._call_callbacks()

    def result(self) -> Any:
        if self._cancelled_event.is_set():
            raise CancelledError
        if self._result_event.is_set():
            return self._result
        if self._exception_event.is_set():
            assert self._exception is not None
            raise self._exception
        raise InvalidStateError

    def set_exception(self, value: BaseException) -> None:
        if self._done:
            raise InvalidStateError
        self._done = True
        self._exception = value
        self._exception_event.set()
        self._call_callbacks()

    def exception(self) -> BaseException | None:
        if not self._done:
            raise InvalidStateError
        if self._cancelled_event.is_set():
            raise CancelledError
        return self._exception

    def add_done_callback(self, callback: Callable[[Future], None]) -> None:
        self._done_callbacks.append(callback)

    def remove_done_callback(self, callback: Callable[[Future], None]) -> int:
        count = self._done_callbacks.count(callback)
        for _ in range(count):
            self._done_callbacks.remove(callback)
        return count
