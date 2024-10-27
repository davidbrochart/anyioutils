import pytest
from anyioutils import CancelledError, Future, InvalidStateError
from anyio import create_task_group

pytestmark = pytest.mark.anyio


async def test_result():
    future = Future()
    with pytest.raises(InvalidStateError):
        future.result()

    async def set_result():
        future.set_result(1)

    async with create_task_group() as tg:
        tg.start_soon(set_result)
        for _ in range(3):
            assert await future.wait() == 1
            assert future.done()
            assert future.result() == 1
        with pytest.raises(InvalidStateError):
            future.set_result(2)


async def test_exception():
    future = Future()
    with pytest.raises(InvalidStateError):
        future.exception()

    async def set_exception():
        future.set_exception(RuntimeError)

    async with create_task_group() as tg:
        tg.start_soon(set_exception)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await future.wait()
            assert future.done()
            assert future.exception() is RuntimeError
            with pytest.raises(RuntimeError):
                future.result()
        with pytest.raises(InvalidStateError):
            future.set_exception(RuntimeError)


async def test_cancel():
    future = Future()
    assert not future.cancelled()

    async def cancel():
        future.cancel()

    async with create_task_group() as tg:
        tg.start_soon(cancel)
        for _ in range(3):
            with pytest.raises(CancelledError):
                await future.wait()
            assert future.done()
            assert future.cancelled()
            with pytest.raises(CancelledError):
                assert future.exception()
            with pytest.raises(CancelledError):
                future.result()


async def test_callback():
    future0 = Future()
    callback0_called = False

    def callback0(future):
        nonlocal callback0_called
        assert future == future0
        callback0_called = True

    future0.add_done_callback(callback0)
    future0.set_result(1)
    assert callback0_called

    future1 = Future()
    callback1_called = False

    def callback1(future):
        nonlocal callback1_called
        assert future == future1  # pragma: no cover
        callback1_called = True  # pragma: no cover

    future1.add_done_callback(callback1)
    future1.remove_done_callback(callback1)
    future1.set_result(1)
    assert not callback1_called

    future2 = Future()

    def callback2(future):
        raise RuntimeError

    future2.add_done_callback(callback2)
    future2.set_result(1)
