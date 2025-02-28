from __future__ import annotations

from typing import Any, Iterable, Literal

from anyio import create_memory_object_stream, move_on_after
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectSendStream

from ._future import Future
from ._task import Task, _task_group


ALL_COMPLETED: Literal["ALL_COMPLETED"] = "ALL_COMPLETED"
FIRST_COMPLETED: Literal["FIRST_COMPLETED"] = "FIRST_COMPLETED"
FIRST_EXCEPTION: Literal["FIRST_EXCEPTION"] = "FIRST_EXCEPTION"


async def _run_and_put_task(
    task: Task | Future,
    send_stream: MemoryObjectSendStream[Any],
):
    exc = None
    try:
        await task.wait()
    except Exception as e:
        exc = e
    try:
        await send_stream.send((task, exc))
    except Exception:
        pass


async def wait(
    aws: Iterable[Task | Future],
    task_group: TaskGroup | None = None,
    *,
    timeout: float | int | None = None,
    return_when: Literal["ALL_COMPLETED", "FIRST_COMPLETED", "FIRST_EXCEPTION"] = ALL_COMPLETED,
) -> tuple[set[Task | Future], set[Task | Future]]:
    """
    Run [Future][anyioutils.Future] and [Task][anyioutils.Task] instances in the *aws* iterable concurrently and block until the condition specified by `return_when`.

    *return_when* indicates when this function should return. It must be one of the following constants:

    | Constant | Description |
    | --- | --- |
    | anyioutils.FIRST_COMPLETED | The function will return when any future finishes or is cancelled. |
    | anyioutils.FIRST_EXCEPTION | The function will return when any future finishes by raising an exception. If no future raises an exception then it is equivalent to [`ALL_COMPLETED`. |
    | anyioutils.ALL_COMPLETED | The function will return when all futures finish or are cancelled. |


    Args:
        timeout: If specified, can be used to control the maximum number of seconds to wait before returning. Note that this function does not raise [TimeoutError](https://docs.python.org/3/library/exceptions.html#TimeoutError). Futures or Tasks that aren't done when the timeout occurs are simply returned in the second set.
        return_when: Indicates when this function should return. It must be one of the following constants:

    Returns:
        Two sets of Tasks/Futures: `(done, pending)`.
    """
    if task_group is None:
        task_group = _task_group.get()
    for aw in aws:
        if not isinstance(aw, (Task, Future)):
            raise TypeError(f"Pass tasks or futures, not {type(aw)}")
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
