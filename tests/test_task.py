from sys import version_info

import pytest
from anyioutils import CancelledError, InvalidStateError, Task, TaskGroup, create_task, start_task
from anyio import Event, TASK_STATUS_IGNORED, create_task_group, sleep
from anyio.abc import TaskStatus

if version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup  # pragma: no cover

pytestmark = pytest.mark.anyio


async def test_task_result1():
    event = Event()

    async def foo():
        event.set()
        return 1

    async with create_task_group() as tg:
        task = Task(foo())
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
        task = create_task(foo(), tg)
        assert await task.wait() == 1


async def test_exception():
    async def foo():
        raise RuntimeError()

    task = Task(foo())
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


async def test_exception_handler():
    expected_exc = None
    actual_exc = None

    async def foo():
        nonlocal expected_exc
        expected_exc = RuntimeError()
        raise expected_exc

    def exception_handler(exc):
        nonlocal actual_exc
        actual_exc = exc
        return True

    async with create_task_group() as tg:
        task = create_task(foo(), tg, exception_handler=exception_handler)
        await task.wait()

    assert expected_exc is not None
    assert expected_exc is actual_exc


async def test_async_exception_handler():
    expected_exc = None
    actual_exc = None

    async def foo():
        nonlocal expected_exc
        expected_exc = RuntimeError()
        raise expected_exc

    async def exception_handler(exc):
        nonlocal actual_exc
        actual_exc = exc
        return True

    async with create_task_group() as tg:
        task = create_task(foo(), tg, exception_handler=exception_handler)
        await task.wait()

    assert expected_exc is not None
    assert expected_exc is actual_exc


async def test_task_cancelled1():
    event = Event()

    async def bar():
        event.set()
        await sleep(float("inf"))

    with pytest.raises(BaseExceptionGroup) as excinfo:
        async with create_task_group() as tg:
            task = create_task(bar(), tg)
            await event.wait()
            task.cancel(raise_exception=True)
            assert task.cancelled()
            with pytest.raises(CancelledError):
                task.exception()
    assert excinfo.group_contains(CancelledError)

    with pytest.raises(CancelledError):
        task.result()


async def test_task_cancelled2():
    event = Event()

    async def bar():
        event.set()
        await sleep(float("inf"))

    with pytest.raises(BaseExceptionGroup) as excinfo:
        async with create_task_group() as tg:
            task = create_task(bar(), tg)
            await event.wait()
            task.cancel(raise_exception=True)
            await task.wait()
    assert excinfo.group_contains(CancelledError)


async def test_task_cancelled3():
    event = Event()

    async def bar():
        event.set()
        await sleep(float("inf"))

    async with create_task_group() as tg:
        task = create_task(bar(), tg)
        await event.wait()
        task.cancel()
        assert await task.wait() is None


async def test_task_cancelled_not_started():
    started = False

    async def bar():
        nonlocal started
        started = True  # pragma: nocover

    async with create_task_group() as tg:
        task = create_task(bar(), tg)
        task.cancel()

    assert not started


async def test_callback():
    async def foo():
        pass

    task0 = Task(foo())
    callback0_called = False

    def callback0(task):
        nonlocal callback0_called
        assert task == task0
        callback0_called = True

    task0.add_done_callback(callback0)
    await task0.wait()
    assert callback0_called

    task1 = Task(foo())
    callback1_called = False

    def callback1(task):
        nonlocal callback1_called
        assert task == task1  # pragma: no cover
        callback1_called = True  # pragma: no cover

    task1.add_done_callback(callback1)
    task1.remove_done_callback(callback1)
    await task1.wait()
    assert not callback1_called

    task2 = Task(foo())

    def callback2(f):
        raise RuntimeError()

    task2.add_done_callback(callback2)

    with pytest.raises(ExceptionGroup):
        await task2.wait()

    task3 = Task(foo())

    def callback3(f):
        raise RuntimeError()

    task3.add_done_callback(callback3)
    task3.add_done_callback(callback3)

    with pytest.raises(ExceptionGroup):
        await task3.wait()


async def test_add_done_callback_already_done():
    async def foo():
        pass

    task = Task(foo())
    await task.wait()
    callback_called = False

    def callback(future):
        nonlocal callback_called
        callback_called = True
        raise RuntimeError()

    with pytest.raises(RuntimeError):
        task.add_done_callback(callback)

    assert callback_called


async def test_start_task():
    async def foo(*, task_status: TaskStatus[None] = TASK_STATUS_IGNORED):
        task_status.started(1)

    async with TaskGroup() as tg:
        task = start_task(foo)
        assert await task.wait_started() == 1
        assert await task.wait() is None
