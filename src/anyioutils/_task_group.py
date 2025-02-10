from contextlib import AsyncExitStack
from typing import Any, Coroutine, TypeVar

from anyio import create_task_group

from ._task import Task, _task_group, create_task as _create_task

T = TypeVar("T")


class TaskGroup:
    async def __aenter__(self) -> "TaskGroup":
        async with AsyncExitStack() as exit_stack:
            tg = await exit_stack.enter_async_context(create_task_group())
            _task_group.set(tg)
            self._exit_stack = exit_stack.pop_all()
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        return await self._exit_stack.__aexit__(exc_type, exc_value, exc_tb)

    def create_task(self, coro: Coroutine[Any, Any, T]) -> Task[T]:
        return _create_task(coro, _task_group.get())
