from sys import version_info

import pytest
from anyioutils import CancelledError, InvalidStateError, create_task
from anyio import Event, create_task_group, sleep

if version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup  # pragma: no cover

pytestmark = pytest.mark.anyio


async def test_task_result1():
    event = Event()

    async def foo():
        event.set()
        return 1

    async with create_task_group() as tg:
        task = create_task(foo())
        with pytest.raises(InvalidStateError):
            task.result()
        tg.start_soon(task.wait)
        await event.wait()
        assert await task.wait() == 1
        assert task.result() == 1


async def test_task_result2():
    async def foo():
        return 1

    async with create_task_group() as tg:
        task = create_task(foo())
        tg.start_soon(task.wait)
        assert await task.wait() == 1


async def test_exception():
    async def foo():
        raise RuntimeError

    task = create_task(foo())
    with pytest.raises(InvalidStateError):
        task.exception()

    async with create_task_group() as tg:
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await task.wait()
            assert task.done()
            assert type(task.exception()) == RuntimeError
            with pytest.raises(RuntimeError):
                task.result()


async def test_task_cancelled1():
    event = Event()

    async def bar():
        event.set()
        await sleep(float("inf"))

    with pytest.raises(BaseExceptionGroup) as excinfo:
        async with create_task_group() as tg:
            task = create_task(bar())
            tg.start_soon(task.wait)
            await event.wait()
            task.cancel()
            assert task.cancelled()
            with pytest.raises(CancelledError):
                task.exception()
    assert len(excinfo.value.exceptions) == 1
    assert type(excinfo.value.exceptions[0]) == CancelledError

    with pytest.raises(CancelledError):
        task.result()


async def test_task_cancelled2():
    event = Event()

    async def bar():
        event.set()
        await sleep(float("inf"))

    with pytest.raises(BaseExceptionGroup) as excinfo:
        async with create_task_group() as tg:
            task = create_task(bar())
            tg.start_soon(task.wait)
            await event.wait()
            task.cancel()
            await task.wait()
    assert type(excinfo.value.exceptions[0]) == CancelledError


async def test_callback():
    async def foo():
        pass

    task0 = create_task(foo())
    callback0_called = False

    def callback0(task):
        nonlocal callback0_called
        assert task == task0
        callback0_called = True

    task0.add_done_callback(callback0)
    await task0.wait()
    assert callback0_called

    task1 = create_task(foo())
    callback1_called = False

    def callback1(task):
        nonlocal callback1_called
        assert task == task1  # pragma: no cover
        callback1_called = True  # pragma: no cover

    task1.add_done_callback(callback1)
    task1.remove_done_callback(callback1)
    await task1.wait()
    assert not callback1_called

    task2 = create_task(foo())

    def callback2(f):
        raise RuntimeError

    task2.add_done_callback(callback2)
    await task2.wait()