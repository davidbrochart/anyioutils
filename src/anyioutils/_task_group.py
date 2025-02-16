from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any, Coroutine, TypeVar

from anyio import CancelScope, create_task_group

from ._task import Task, _task_group, create_task as _create_task

T = TypeVar("T")


class TaskGroup:
    @property
    def cancel_scope(self) -> CancelScope:
        return self._task_group.cancel_scope

    async def __aenter__(self) -> "TaskGroup":
        async with AsyncExitStack() as exit_stack:
            self._task_group = await exit_stack.enter_async_context(create_task_group())
            self._token = _task_group.set(self._task_group)
            self._exit_stack = exit_stack.pop_all()
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        _task_group.reset(self._token)
        return await self._exit_stack.__aexit__(exc_type, exc_value, exc_tb)

    def create_task(self, coro: Coroutine[Any, Any, T], *, name: str | None = None) -> Task[T]:
        return _create_task(coro, self._task_group, name=name)
