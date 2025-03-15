from __future__ import annotations

from contextlib import AsyncExitStack
from types import TracebackType
from typing import Any, Coroutine, TypeVar

from anyio import CancelScope, create_task_group

from ._task import Task, _task_group, create_task as _create_task

T = TypeVar("T")


class TaskGroup:
    """
    An [asynchronous context manager](https://docs.python.org/3/reference/datamodel.html#async-context-managers) holding a group of tasks. Tasks can be added to the group using [create_task()][anyioutils.TaskGroup.create_task]. All tasks are awaited when the context manager exits, unless they have been created with `background=True`.

    Tasks created down the call stack using [create_task()][anyioutils.create_task] or [start_task()][anyioutils.start_task] may not need to be passed a TaskGroup, since they could use this TaskGroup implicitly.
    """
    def __init__(self):
        self._background_tasks = []

    @property
    def cancel_scope(self) -> CancelScope:
        """
        Returns:
            The TaskGroup's [CancelScope](https://anyio.readthedocs.io/en/stable/api.html#anyio.CancelScope).
        """
        return self._task_group.cancel_scope

    async def __aenter__(self) -> "TaskGroup":
        async with AsyncExitStack() as exit_stack:
            self._task_group = await exit_stack.enter_async_context(create_task_group())
            self._token = _task_group.set(self._task_group)
            self._exit_stack = exit_stack.pop_all()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        _task_group.reset(self._token)
        for task in self._background_tasks:
            task.cancel()
        await self._exit_stack.__aexit__(exc_type, exc_value, exc_tb)

    def create_task(self, coro: Coroutine[Any, Any, T], *, name: str | None = None, background: bool = False) -> Task[T]:
        """
        Create a task in this task group.

        Args:
            background: Whether to run the task in the background, in which case it will be cancelled when the task group exits.
            name: The task name.
        Returns:
            The created Task.
        """
        task = _create_task(coro, self._task_group, name=name)
        if background:
            self._background_tasks.append(task)
        return task
