from __future__ import annotations

from typing import Any, Callable
from collections.abc import Coroutine

from anyio import Event, create_task_group
from anyio.abc import TaskGroup

from ._exceptions import CancelledError, InvalidStateError


class Task:
    _done_callbacks: list[Callable[[Task], None]]
    _exception: BaseException | None

    def __init__(self, coro: Coroutine[Any, Any, Any]) -> None:
        self._coro = coro
        self._has_result = False
        self._has_exception = False
        self._cancelled_event = Event()
        self._done_callbacks = []
        self._done = False
        self._exception = None

    def _call_callbacks(self) -> None:
        for callback in self._done_callbacks:
            try:
                callback(self)
            except BaseException:
                pass

    async def _wait_result(self, task_group: TaskGroup) -> None:
        if self._done:
            task_group.cancel_scope.cancel()
            return

        try:
            self._result = await self._coro
            self._has_result = True
        except BaseException as exc:
            self._exception = exc
            self._has_exception = True
        self._done = True
        task_group.cancel_scope.cancel()
        self._call_callbacks()

    async def _wait_cancelled(self, task_group: TaskGroup) -> None:
        await self._cancelled_event.wait()
        task_group.cancel_scope.cancel()

    def cancel(self):
        self._done = True
        self._cancelled_event.set()
        self._call_callbacks()

    def cancelled(self) -> bool:
        return self._cancelled_event.is_set()

    async def wait(self) -> Any:
        if self._has_result:
            return self._result
        if self._cancelled_event.is_set():
            raise CancelledError
        if self._has_exception:
            assert self._exception is not None
            raise self._exception

        async with create_task_group() as tg:
            tg.start_soon(self._wait_result, tg)
            tg.start_soon(self._wait_cancelled, tg)

        if self._has_result:
            return self._result
        if self._cancelled_event.is_set():
            raise CancelledError
        if self._has_exception:
            assert self._exception is not None
            raise self._exception
        raise RuntimeError(  # pragma: no cover
            "Task has no result, no exception, and was not cancelled"
        )

    def done(self) -> bool:
        return self._done

    def result(self) -> Any:
        if self._cancelled_event.is_set():
            raise CancelledError
        if self._has_result:
            return self._result
        if self._has_exception:
            assert self._exception is not None
            raise self._exception
        raise InvalidStateError

    def exception(self) -> BaseException | None:
        if not self._done:
            raise InvalidStateError
        if self._cancelled_event.is_set():
            raise CancelledError
        return self._exception

    def add_done_callback(self, callback: Callable[[Task], None]) -> None:
        self._done_callbacks.append(callback)

    def remove_done_callback(self, callback: Callable[[Task], None]) -> int:
        count = self._done_callbacks.count(callback)
        for _ in range(count):
            self._done_callbacks.remove(callback)
        return count


def create_task(coro: Coroutine[Any, Any, Any]) -> Task:
    return Task(coro)