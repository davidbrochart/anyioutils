# anyioutils

Utility classes and functions for AnyIO.

## Task

`task = anyioutils.create_task(my_async_func())` behaves the same as `task = asyncio.create_task(my_async_func())` except that:
- the `task` still has to be launched in the background with an existing task group `tg`, using `tg.start_soon(task.wait)`,
- and/or the `task` can be awaited with `result = await task.wait()`.

```py
from anyioutils import CancelledError, create_task
from anyio import create_task_group, run, sleep

async def foo():
    return 1

async def bar():
    await sleep(float("inf"))

async def main():
    async with create_task_group() as tg:
        task = create_task(foo())
        assert await task.wait() == 1

    try:
        async with create_task_group() as tg:
            task = create_task(bar())
            tg.start_soon(task.wait)
            await sleep(0.1)
            task.cancel()
    except ExceptionGroup as exc_group:
        assert len(exc_group.exceptions) == 1
        assert type(exc_group.exceptions[0]) == CancelledError

run(main)
```

## Future

`anyioutils.Future` behaves the same as `asyncio.Future` except that:
- you cannot directly await an `anyioutils.Future` object, but through its `.wait()` method (unlike an `asyncio.Future`, but like an `asyncio.Event`),
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
