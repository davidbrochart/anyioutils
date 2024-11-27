from __future__ import annotations

from typing import Any, Literal

from anyio import ClosedResourceError, create_memory_object_stream, move_on_after
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectSendStream

from ._task import Task


ALL_COMPLETED = "ALL_COMPLETED"
FIRST_COMPLETED = "FIRST_COMPLETED"
FIRST_EXCEPTION = "FIRST_EXCEPTION"


async def _run_and_put_task(
    task: Task,
    send_stream: MemoryObjectSendStream[Any],
):
    exc = None
    try:
        await task.wait()
    except Exception as e:
        exc = e
    try:
        await send_stream.send((task, exc))
    except ClosedResourceError:
        pass


async def wait(
    aws,
    task_group: TaskGroup,
    *,
    timeout: float | int | None = None,
    return_when: Literal["ALL_COMPLETED", "FIRST_COMPLETED", "FIRST_EXCEPTION"] = "ALL_COMPLETED",
):
    for aw in aws:
        if not isinstance(aw, Task):
            raise TypeError(f"Pass tasks, not {type(aw)}")
    if timeout is None:
        timeout = float("inf")
    done = set()
    pending = set(aws)
    send_stream, receive_stream = create_memory_object_stream[Any]()
    async with send_stream, receive_stream:
        for task in aws:
            task_group.start_soon(_run_and_put_task, task, send_stream)
        with move_on_after(timeout):
            async for aw_exc in receive_stream:
                aw, exc = aw_exc
                done.add(aw)
                pending.remove(aw)
                if return_when == FIRST_EXCEPTION and exc is not None:
                    break
                if return_when == FIRST_COMPLETED:
                    break
                if not pending:
                    break
        return done, pending
