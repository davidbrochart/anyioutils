import pytest

from anyio import move_on_after
from anyioutils import Event

pytestmark = pytest.mark.anyio


async def test_event():
    event = Event()
    assert not event.is_set()
    event.set()
    assert event.is_set()
    await event.wait()
    event.clear()
    with move_on_after(0.1):
        await event.wait()
    assert not event.is_set()
