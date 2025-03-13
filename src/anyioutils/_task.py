from __future__ import annotations

from inspect import isawaitable
from sys import version_info
from collections.abc import Awaitable, Coroutine
from contextvars import ContextVar
from typing import Any, Callable, Generic, TypeVar

from anyio import Event, create_task_group
from anyio.abc import TaskGroup

from ._exceptions import CancelledError, InvalidStateError
from ._queue import Queue

if version_info < (3, 10):  # pragma: no cover
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias  # type: ignore[attr-defined,no-redef]

if version_info < (3, 11):  # pragma: no cover
    from exceptiongroup import BaseExceptionGroup  # type: ignore[import-not-found]


T = TypeVar("T")
ExceptionHandler: TypeAlias = Callable[[BaseException], Any]
_task_group: ContextVar[TaskGroup] = ContextVar("_task_group")


async def ensure_awaitable(obj: T | Awaitable[T]) -> T:
    if isawaitable(obj):
        return await obj
    return obj


class Task(Generic[T]):
    """
    A Future-like object that runs a Python [coroutine](https://docs.python.org/3/library/asyncio-task.html#coroutine). Not thread-safe.

    Tasks are used to run coroutines in event loops. If a coroutine awaits on a Future, the Task suspends the execution of the coroutine and waits for the completion of the Future. When the Future is done, the execution of the wrapped coroutine resumes.

    Event loops use cooperative scheduling: an event loop runs one Task at a time. While a Task awaits for the completion of a Future, the event loop runs other Tasks, callbacks, or performs IO operations.

    Use the high-level [anyioutils.create_task()][anyioutils.create_task] function to create Tasks. Manual instantiation of Tasks is discouraged.

    To cancel a running Task use the [cancel()][anyioutils.Task.cancel] method. Calling it will cause the Task to throw a [CancelledError][anyioutils.CancelledError] exception into the wrapped coroutine. If a coroutine is awaiting on a Future object during cancellation, the Future object will be cancelled.

    [cancelled()][anyioutils.Task.cancelled] can be used to check if the Task was cancelled.
    """
    _done_callbacks: list[Callable[[Task], None]]
    _exception: BaseException | None
    _result: T | None

    def __init__(self, coro: Coroutine[Any, Any, T], exception_handler: ExceptionHandler | None = None) -> None:
        self._coro = coro
        self._exception_handler = exception_handler
        self._has_result = False
        self._has_exception = False
        self._coro_started = False
        self._cancelled_event = Event()
        self._raise_cancelled_error = True
        self._done_callbacks = []
        self._done_event = Event()
        self._exception = None
        self._waiting = False
        self._started_value = Queue[Any]()

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
            self._coro_started = True
            self._result = await self._coro
            self._has_result = True
        except BaseException as exc:
            if self._exception_handler is None or not await ensure_awaitable(self._exception_handler(exc)):
                self._exception = exc
                self._has_exception = True
            else:
                self._result = None
                self._has_result = True
        self._done_event.set()
        task_group.cancel_scope.cancel()
        self._call_callbacks()

    async def _wait_cancelled(self, task_group: TaskGroup) -> None:
        await self._cancelled_event.wait()
        task_group.cancel_scope.cancel()

    def cancel(self, raise_exception: bool = False) -> None:
        """
        Request the Task to be cancelled.
        """
        if not self._coro_started:
            self._coro.close()
        self._done_event.set()
        self._cancelled_event.set()
        self._raise_cancelled_error = raise_exception
        self._call_callbacks()

    def cancelled(self) -> bool:
        """
        Returns:
            `True` if the Task is *cancelled*.
        """
        return self._cancelled_event.is_set()

    async def wait(self) -> T | None:
        """
        Wait for the Task to be *done* or *cancelled*.

        Returns:
            The return value of the coroutine, if not *cancelled*, otherwise `None`.
        """
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
        """
        A Task is *done* when the wrapped coroutine either returned a value, raised an exception, or the Task was cancelled.

        Return:
            `True` if the Task is done.
        """
        return self._done_event.is_set()

    def result(self) -> T | None:
        """
        If the Task is *done*, the result of the wrapped coroutine is returned (or if the coroutine raised an exception, that exception is re-raised).

        If the Task has been *cancelled*, this method raises a [CancelledError][anyioutils.CancelledError] exception.

        If the Task's result is't yet available, this method raises an [InvalidStateError][anyioutils.InvalidStateError] exception.

        Return:
            The result of the Task.
        """
        if self._cancelled_event.is_set():
            raise CancelledError
        if self._has_result:
            return self._result
        if self._has_exception:
            assert self._exception is not None
            raise self._exception
        raise InvalidStateError

    def exception(self) -> BaseException | None:
        """
        If the wrapped coroutine raised an exception that exception is returned. If the wrapped coroutine returned normally this method returns `None`.

        If the Task has been *cancelled*, this method raises a [CancelledError][anyioutils.CancelledError] exception.

        If the Task isn't done yet, this method raises an [InvalidStateError][anyioutils.InvalidStateError] exception.

        Returns:
            The exception of the Task.
        """
        if not self._done_event.is_set():
            raise InvalidStateError
        if self._cancelled_event.is_set():
            raise CancelledError
        return self._exception

    def add_done_callback(self, callback: Callable[[Task], None]) -> None:
        """
        Add a callback to be run when the Task is *done*.

        This method should only be used in low-level callback-based code.

        See the documentation of [Future.add_done_callback()][anyioutils.Future.add_done_callback] for more details.
        """
        self._done_callbacks.append(callback)
        if self._done_event.is_set():
            callback(self)

    def remove_done_callback(self, callback: Callable[[Task], None]) -> int:
        """
        Remove *callback* from the callbacks list.

        This method should only be used in low-level callback-based code.

        See the documentation of [Future.remove_done_callback()][anyioutils.Future.remove_done_callback] for more details.
        """
        count = self._done_callbacks.count(callback)
        for _ in range(count):
            self._done_callbacks.remove(callback)
        return count

    async def wait_started(self) -> Any:
        """
        Wait for the task to be [started](https://anyio.readthedocs.io/en/stable/tasks.html#starting-and-initializing-tasks).
        The task must have been created with [start_task()][anyioutils.start_task], not [create_task][anyioutils.create_task].

        Returns:
            The started value.
        """
        return await self._started_value.get()


def create_task(
    coro: Coroutine[Any, Any, T],
    task_group: TaskGroup | None = None,
    *,
    name: str | None = None,
    exception_handler: ExceptionHandler | None = None,
) -> Task[T]:
    """
    Wrap the *coro* [coroutine](https://docs.python.org/3/library/asyncio-task.html#coroutine) into a [Task][anyioutils.Task] and schedule its execution.

    Args:
        task_group: An optional [TaskGroup](https://anyio.readthedocs.io/en/stable/api.html#anyio.abc.TaskGroup) (from AnyIO) to run the Task in. If not provided, a [TaskGroup][anyioutils.TaskGroup] (from `anyioutils`) will be looked up the call stack and used if found.
        exception_handler: An optional exception handler. When an exception occurs in the Task, the exception handler is called with the exception. The exception is considered to be handled if the exception handler returns `True`, otherwise the exception is raised.

    Returns:
        The Task object.
    """
    task = Task[T](coro, exception_handler)
    if task_group is None:
        task_group = _task_group.get()
    task_group.start_soon(task.wait, name=name)
    return task


def start_task(
    async_fn: Callable[..., Awaitable[Any]],
    task_group: TaskGroup | None = None,
    *,
    name: str | None = None,
    exception_handler: ExceptionHandler | None = None,
) -> Task[None]:
    """
    Create a [coroutine](https://docs.python.org/3/library/asyncio-task.html#coroutine) from the *async_fn* async function, wrap it into a [Task][anyioutils.Task] and schedule its execution.

    The Task's [wait()][anyioutils.Task.wait] method will only return `None`, but its [wait_started()][anyioutils.Task.wait_started] method will return its started value.

    Args:
        task_group: An optional [TaskGroup](https://anyio.readthedocs.io/en/stable/api.html#anyio.abc.TaskGroup) (from AnyIO) to run the Task in. If not provided, a [TaskGroup][anyioutils.TaskGroup] (from `anyioutils`) will be looked up the call stack and used, if found.
        exception_handler: An optional exception handler. When an exception occurs in the Task, the exception handler is called with the exception. The exception is considered to be handled if the exception handler returns `True`, otherwise the exception is raised.

    Returns:
        The Task object.
    """
    async_function_wrapper = AsyncFunctionWrapper(async_fn)
    task = Task[None](async_function_wrapper.get_coro(), exception_handler)
    async_function_wrapper.set_task(task)
    if task_group is None:
        task_group = _task_group.get()
    task_group.start_soon(task.wait, name=name)
    return task


class AsyncFunctionWrapper:
    def __init__(self, async_fn: Callable[..., Awaitable[T]]) -> None:
        self._async_fn = async_fn

    def set_task(self, task: Task) -> None:
        self._task = task

    async def get_coro(self) -> None:
        async with create_task_group() as tg:
            started_value = await tg.start(self._async_fn)
            await self._task._started_value.put(started_value)
