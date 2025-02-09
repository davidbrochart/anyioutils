import pytest

import anyio
from anyioutils import Queue

pytestmark = pytest.mark.anyio


def test_queue_nowait():
    queue = Queue(1)
    assert queue.maxsize == 1
    assert queue.qsize() == 0
    assert queue.empty()
    assert not queue.full()
    queue.put_nowait("foo")
    assert not queue.empty()
    assert queue.full()
    assert queue.qsize() == 1

    with pytest.raises(anyio.WouldBlock):
        queue.put_nowait("bar")

    assert queue.qsize() == 1
    assert queue.get_nowait() == "foo"
    assert queue.qsize() == 0
    assert queue.empty()
    assert not queue.full()


async def test_queue():
    queue = Queue()
    assert queue.maxsize == 0
    assert queue.qsize() == 0
    assert queue.empty()
    assert not queue.full()
    await queue.put("foo")
    assert not queue.empty()
    assert not queue.full()
    assert queue.qsize() == 1
    await queue.put("bar")
    assert queue.qsize() == 2
    assert await queue.get() == "foo"
    assert queue.qsize() == 1
    assert not queue.empty()
    assert not queue.full()
    assert await queue.get() == "bar"
    assert queue.qsize() == 0
    assert queue.empty()
    assert not queue.full()
