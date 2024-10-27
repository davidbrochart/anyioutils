from __future__ import annotations

from typing import Any
from collections.abc import Coroutine

from anyio import Event, create_task_group
from anyio.abc import TaskGroup

from ._exceptions import CancelledError


class Task:
    def __init__(self, coro: Coroutine[Any, Any, Any]) -> None:
        self._coro = coro
        self._has_result = False
        self._cancelled_event = Event()

    def cancel(self):
        self._cancelled_event.set()

    async def wait(self) -> Any:
        if self._cancelled_event.is_set():
            raise CancelledError
        if self._has_result:
            return self._result

        async with create_task_group() as tg:
            tg.start_soon(self._wait_result, tg)
            tg.start_soon(self._wait_cancelled, tg)

        if self._cancelled_event.is_set():
            raise CancelledError
        if self._has_result:
            return self._result
        raise RuntimeError("Task has no result and was not cancelled")  # pragma: no cover

    async def _wait_result(self, task_group: TaskGroup) -> None:
        if self._has_result:
            task_group.cancel_scope.cancel()
            return

        self._result = await self._coro
        self._has_result = True
        task_group.cancel_scope.cancel()

    async def _wait_cancelled(self, task_group: TaskGroup) -> None:
        await self._cancelled_event.wait()
        task_group.cancel_scope.cancel()


def create_task(coro: Coroutine[Any, Any, Any]) -> Task:
    return Task(coro)
