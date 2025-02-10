from __future__ import annotations

from sys import version_info
from typing import Callable, Generic, TypeVar

from anyio import Event, create_task_group
from anyio.abc import TaskGroup

from ._exceptions import CancelledError, InvalidStateError

if version_info < (3, 11):  # pragma: no cover
    from exceptiongroup import BaseExceptionGroup  # type: ignore[import-not-found]

T = TypeVar("T")


class Future(Generic[T]):
    _done_callbacks: list[Callable[[Future], None]]
    _exception: BaseException | None

    def __init__(self) -> None:
        self._result_event = Event()
        self._exception_event = Event()
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
        await self._result_event.wait()
        task_group.cancel_scope.cancel()

    async def _wait_exception(self, task_group: TaskGroup) -> None:
        await self._exception_event.wait()
        task_group.cancel_scope.cancel()

    async def _wait_cancelled(self, task_group: TaskGroup) -> None:
        await self._cancelled_event.wait()
        task_group.cancel_scope.cancel()

    def cancel(self, raise_exception: bool = False) -> bool:
        if self._done_event.is_set() or self._cancelled_event.is_set():
            return False

        self._done_event.set()
        self._cancelled_event.set()
        self._raise_cancelled_error = raise_exception
        self._call_callbacks()
        return True

    def cancelled(self) -> bool:
        return self._cancelled_event.is_set()

    async def wait(self) -> T | None:
        if self._waiting:
            await self._done_event.wait()
        self._waiting = True
        if self._result_event.is_set():
            return self._result
        if self._exception_event.is_set():
            assert self._exception is not None
            raise self._exception
        if self._cancelled_event.is_set():
            if self._raise_cancelled_error:
                raise CancelledError

        async with create_task_group() as tg:
            tg.start_soon(self._wait_result, tg)
            tg.start_soon(self._wait_exception, tg)
            tg.start_soon(self._wait_cancelled, tg)

        if self._result_event.is_set():
            return self._result
        if self._exception_event.is_set():
            assert self._exception is not None
            raise self._exception
        if self._cancelled_event.is_set():
            if self._raise_cancelled_error:
                raise CancelledError

        return None  # pragma: nocover

    def done(self) -> bool:
        return self._done_event.is_set()

    def set_result(self, value: T) -> None:
        if self._done_event.is_set():
            raise InvalidStateError
        self._done_event.set()
        self._result = value
        self._result_event.set()
        self._call_callbacks()

    def result(self) -> T:
        if self._cancelled_event.is_set():
            raise CancelledError
        if self._result_event.is_set():
            return self._result
        if self._exception_event.is_set():
            assert self._exception is not None
            raise self._exception
        raise InvalidStateError

    def set_exception(self, value: BaseException) -> None:
        if self._done_event.is_set():
            raise InvalidStateError
        self._done_event.set()
        self._exception = value
        self._exception_event.set()
        self._call_callbacks()

    def exception(self) -> BaseException | None:
        if not self._done_event.is_set():
            raise InvalidStateError
        if self._cancelled_event.is_set():
            raise CancelledError
        return self._exception

    def add_done_callback(self, callback: Callable[[Future], None]) -> None:
        self._done_callbacks.append(callback)
        if self._done_event.is_set():
            callback(self)

    def remove_done_callback(self, callback: Callable[[Future], None]) -> int:
        count = self._done_callbacks.count(callback)
        for _ in range(count):
            self._done_callbacks.remove(callback)
        return count
