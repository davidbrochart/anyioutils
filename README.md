# anyioutils

`anyioutils.Future` behaves the same as `asyncio.Future` except that:
- you cannot directly await an `anyioutils.Future` object, but through its `.wait()` method (unlike an `asyncio.Future`, but like an `asyncio.Event`).
- cancelling an `anyioutils.Future` doesn't raise an `anyio.get_cancelled_exc_class()`, but an `anyioutils.CancelledError`.

```py
from anyioutils import CancelledError, Future
from anyio import create_task_group, run

async def set_result(future):
    future.set_result("done")

async def cancel(future):
    future.cancel()

async def main():
    async with create_task_group() as tg:
        future0 = Future()
        tg.start_soon(set_result, future0)
        assert await future0.wait() == "done"

        future1 = Future()
        tg.start_soon(cancel, future1)
        try:
            await future1.wait()
        except CancelledError:
            assert future1.cancelled()

run(main)
```
