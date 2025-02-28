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
    """
    A Future represents an eventual result of an asynchronous operation. Not thread-safe.

    Future is an [awaitable](https://docs.python.org/3/glossary.html#term-awaitable) object.
    Coroutines can await on Future objects until they either have a result or an exception set,
    or until they are cancelled. A Future can be awaited multiple times and the result is same.

    Typically Futures are used to enable low-level callback-based code to interoperate with high-level async/await code.
    """

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
        """
        Cancel the Future and schedule callbacks.

        If the Future is already *done* or *cancelled*, return `False`.
        Otherwise, change the Future's state to *cancelled*, schedule the callbacks, and return `True`.

        Args:
            raise_exception: Whether to raise a [CancelledError][anyioutils.CancelledError].

        Returns:
            `False` if the Future is already *done* or *cancelled*, `True` otherwise.
        """
        if self._done_event.is_set() or self._cancelled_event.is_set():
            return False

        self._done_event.set()
        self._cancelled_event.set()
        self._raise_cancelled_error = raise_exception
        self._call_callbacks()
        return True

    def cancelled(self) -> bool:
        """
        Returns:
            `True` if the Future was cancelled, `False` otherwise.
        """
        return self._cancelled_event.is_set()

    async def wait(self) -> T | None:
        """
        Wait for the Future to be *done* or *cancelled*.

        Returns:
            The Furure's return value.
        """
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
        """
        A Future is *done* if it was *cancelled* or if it has a result or an exception set with [set_result()][anyioutils.Future.set_result] or [set_exception()][anyioutils.Future.set_exception] calls.

        Returns:
            `True` if the Future is *done*.
        """
        return self._done_event.is_set()

    def set_result(self, value: T) -> None:
        """
        Mark the Future as *done* and set its result.

        Raises:
            InvalidStateError: The Future is already *done*.
        """
        if self._done_event.is_set():
            raise InvalidStateError
        self._done_event.set()
        self._result = value
        self._result_event.set()
        self._call_callbacks()

    def result(self) -> T:
        """
        If the Future is *done* and has a result set by the [set_result()][anyioutils.Future.set_result] method, the result value is returned.

        If the Future is *done* and has an exception set by the [set_exception()][anyioutils.Future.set_exception] method, this method raises the exception.

        If the Future has been *cancelled*, this method raises a [CancelledError][anyioutils.CancelledError] exception.

        If the Future’s result isn’t yet available, this method raises an [InvalidStateError][anyioutils.InvalidStateError] exception.

        Returns:
            The result of the Future.
        """
        if self._cancelled_event.is_set():
            raise CancelledError
        if self._result_event.is_set():
            return self._result
        if self._exception_event.is_set():
            assert self._exception is not None
            raise self._exception
        raise InvalidStateError

    def set_exception(self, value: BaseException) -> None:
        """
        Mark the Future as *done* and set an exception.

        Raises:
            InvalidStateError: The Future is already *done*.
        """
        if self._done_event.is_set():
            raise InvalidStateError
        self._done_event.set()
        self._exception = value
        self._exception_event.set()
        self._call_callbacks()

    def exception(self) -> BaseException | None:
        """
        The exception (or `None` if no exception was set) is returned only if the Future is *done*.

        If the Future has been *cancelled*, this method raises a [CancelledError][anyioutils.CancelledError] exception.

        If the Future isn’t *done* yet, this method raises an [InvalidStateError][anyioutils.InvalidStateError] exception.

        Returns:
            The exception that was set on this Future.
        """
        if not self._done_event.is_set():
            raise InvalidStateError
        if self._cancelled_event.is_set():
            raise CancelledError
        return self._exception

    def add_done_callback(self, callback: Callable[[Future], None]) -> None:
        """
        Add a callback to be run when the Future is *done*.

        The *callback* is called with the Future object as its only argument.

        If the Future is already *done* when this method is called, the callback is scheduled immediately.
        """
        self._done_callbacks.append(callback)
        if self._done_event.is_set():
            callback(self)

    def remove_done_callback(self, callback: Callable[[Future], None]) -> int:
        """
        Remove *callback* from the callbacks list.

        Returns:
            The number of callbacks removed, which is typically 1, unless a callback was added more than once.
        """
        count = self._done_callbacks.count(callback)
        for _ in range(count):
            self._done_callbacks.remove(callback)
        return count
