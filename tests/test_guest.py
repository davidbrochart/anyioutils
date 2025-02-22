import asyncio
import queue

import pytest
import trio
from anyioutils import start_guest_run


# copied from: https://trio.readthedocs.io/en/stable/reference-lowlevel.html#implementing-guest-mode-for-your-favorite-event-loop
def test_host_asyncio_guest_trio():
    results = []

    async def trio_main():
        for _ in range(5):
            results.append("Hello from trio!")
            await trio.sleep(0.1)
        return "trio done!"
    
    async def asyncio_main():
        asyncio_loop = asyncio.get_running_loop()
    
        def run_sync_soon_threadsafe(fn):
            asyncio_loop.call_soon_threadsafe(fn)
    
        def done_callback(trio_main_outcome):
            results.append(f"Trio program ended with: {trio_main_outcome}")
    
        start_guest_run(
            trio_main,
            run_sync_soon_threadsafe=run_sync_soon_threadsafe,
            done_callback=done_callback,
            backend="trio",
        )
    
        await asyncio.sleep(1)
    
    asyncio.run(asyncio_main())

    assert results == ["Hello from trio!"] * 5 + ["Trio program ended with: Value('trio done!')"]


# copied from: https://github.com/oremanj/aioguest/blob/b9480a01600d44f8d35e78c7f6689f187331df64/tests/test_basic.py#L52
def test_host_trivial_guest_asyncio():
    results = []
    todo = queue.Queue()

    async def asyncio_main():
        for _ in range(5):
            results.append("Hello from asyncio!")
            await asyncio.sleep(0.1)
        return "asyncio done!"

    def run_sync_soon_threadsafe(fn):
        todo.put(("run", fn))

    def done_callback(result):
        todo.put(("done", result))

    start_guest_run(
        asyncio_main,
        run_sync_soon_threadsafe=run_sync_soon_threadsafe,
        done_callback=done_callback,
        backend="asyncio",
    )

    while True:
        op, obj = todo.get()
        if op == "run":
            obj()  # pragma: nocover
        elif op == "done":
            results.append(f"Asyncio program ended with: {obj}")
            break

    assert results == ["Hello from asyncio!"] * 5 + ["Asyncio program ended with: Value('asyncio done!')"]


def test_wrong_backend():
    async def main(): pass

    def run_sync_soon_threadsafe(fn): pass

    def done_callback(result): pass
    
    with pytest.raises(RuntimeError) as excinfo:
        start_guest_run(
            main,
            run_sync_soon_threadsafe=run_sync_soon_threadsafe,
            done_callback=done_callback,
            backend="foo",
        )

    assert str(excinfo.value) == 'Backend not supported: "foo"'


def test_not_coroutine_function():
    def run_sync_soon_threadsafe(fn): pass

    def done_callback(result): pass
    
    with pytest.raises(RuntimeError) as excinfo:
        start_guest_run(
            None,
            run_sync_soon_threadsafe=run_sync_soon_threadsafe,
            done_callback=done_callback,
            backend="asyncio",
        )

    assert str(excinfo.value) == "Expected a coroutine function, got: None"
