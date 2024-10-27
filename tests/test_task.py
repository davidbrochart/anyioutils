from sys import version_info

import pytest
from anyioutils import CancelledError, create_task
from anyio import Event, create_task_group, sleep

if version_info < (3, 11):
    from exceptiongroup import ExceptionGroup  # pragma: no cover

pytestmark = pytest.mark.anyio


async def test_task_result1():
    event = Event()

    async def foo():
        event.set()
        return 1

    async with create_task_group() as tg:
        task = create_task(foo())
        tg.start_soon(task.wait)
        await event.wait()
        assert await task.wait() == 1


async def test_task_result2():
    async def foo():
        return 1

    async with create_task_group() as tg:
        task = create_task(foo())
        tg.start_soon(task.wait)
        assert await task.wait() == 1


async def test_task_cancelled1():
    event = Event()

    async def bar():
        event.set()
        await sleep(float("inf"))

    with pytest.raises(ExceptionGroup) as excinfo:
        async with create_task_group() as tg:
            task = create_task(bar())
            tg.start_soon(task.wait)
            await event.wait()
            task.cancel()
    assert len(excinfo.value.exceptions) == 1
    assert type(excinfo.value.exceptions[0]) == CancelledError


async def test_task_cancelled2():
    event = Event()

    async def bar():
        event.set()
        await sleep(float("inf"))

    with pytest.raises(ExceptionGroup) as excinfo:
        async with create_task_group() as tg:
            task = create_task(bar())
            tg.start_soon(task.wait)
            await event.wait()
            task.cancel()
            await task.wait()
    assert len(excinfo.value.exceptions) == 1
    assert type(excinfo.value.exceptions[0]) == CancelledError
