from __future__ import annotations

from sys import version_info
from collections.abc import Coroutine
from contextvars import ContextVar
from typing import Any, Callable, Generic, TypeVar

from anyio import Event, create_task_group
from anyio.abc import TaskGroup

from ._exceptions import CancelledError, InvalidStateError

if version_info < (3, 11):  # pragma: no cover
    from exceptiongroup import BaseExceptionGroup  # type: ignore[import-not-found]


T = TypeVar("T")
_task_group: ContextVar[TaskGroup] = ContextVar("_task_group")


class Task(Generic[T]):
    _done_callbacks: list[Callable[[Task], None]]
    _exception: BaseException | None

    def __init__(self, coro: Coroutine[Any, Any, T]) -> None:
        self._coro = coro
        self._has_result = False
        self._has_exception = False
        self._cancelled_event = Event()
        self._raise_cancelled_error = True
        self._done_callbacks = []
        self._done_event = Event()
        self._exception = None
        self._waiting = False

    def _call_callbacks(self) -> None:
        exceptions = []
        for callback in self._done_callbacks:
            try:
                callback(self)
            except BaseException as exc:
                exceptions.append(exc)
        if not exceptions:
            return
        if len(exceptions) == 1:
            raise exceptions[0]
        raise BaseExceptionGroup("Error while calling callbacks", exceptions)

    async def _wait_result(self, task_group: TaskGroup) -> None:
        try:
            self._result = await self._coro
            self._has_result = True
        except BaseException as exc:
            self._exception = exc
            self._has_exception = True
        self._done_event.set()
        task_group.cancel_scope.cancel()
        self._call_callbacks()

    async def _wait_cancelled(self, task_group: TaskGroup) -> None:
        await self._cancelled_event.wait()
        task_group.cancel_scope.cancel()

    def cancel(self, raise_exception: bool = False):
        self._done_event.set()
        self._cancelled_event.set()
        self._raise_cancelled_error = raise_exception
        self._call_callbacks()

    def cancelled(self) -> bool:
        return self._cancelled_event.is_set()

    async def wait(self) -> T | None:
        if self._waiting:
            await self._done_event.wait()
        self._waiting = True
        if self._has_result:
            return self._result
        if self._cancelled_event.is_set():
            if self._raise_cancelled_error:
                raise CancelledError
            return None
        if self._has_exception:
            assert self._exception is not None
            raise self._exception

        async with create_task_group() as tg:
            tg.start_soon(self._wait_result, tg)
            tg.start_soon(self._wait_cancelled, tg)

        if self._has_result:
            return self._result
        if self._cancelled_event.is_set():
            if self._raise_cancelled_error:
                raise CancelledError
            return None
        if self._has_exception:
            assert self._exception is not None
            raise self._exception

        return None  # pragma: nocover

    def done(self) -> bool:
        return self._done_event.is_set()

    def result(self) -> T:
        if self._cancelled_event.is_set():
            raise CancelledError
        if self._has_result:
            return self._result
        if self._has_exception:
            assert self._exception is not None
            raise self._exception
        raise InvalidStateError

    def exception(self) -> BaseException | None:
        if not self._done_event.is_set():
            raise InvalidStateError
        if self._cancelled_event.is_set():
            raise CancelledError
        return self._exception

    def add_done_callback(self, callback: Callable[[Task], None]) -> None:
        self._done_callbacks.append(callback)
        if self._done_event.is_set():
            callback(self)

    def remove_done_callback(self, callback: Callable[[Task], None]) -> int:
        count = self._done_callbacks.count(callback)
        for _ in range(count):
            self._done_callbacks.remove(callback)
        return count


def create_task(coro: Coroutine[Any, Any, T], task_group: TaskGroup | None = None, *, name: str | None = None) -> Task[T]:
    task = Task[T](coro)
    if task_group is None:
        task_group = _task_group.get()
    task_group.start_soon(task.wait, name=name)
    return task
