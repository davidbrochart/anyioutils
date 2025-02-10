[![Build Status](https://github.com/davidbrochart/anyioutils/actions/workflows/test.yml/badge.svg?query=branch%3Amain++)](https://github.com/davidbrochart/anyioutils/actions/workflows/test.yml/badge.svg?query=branch%3Amain++)
[![Code Coverage](https://img.shields.io/badge/coverage-100%25-green)](https://img.shields.io/badge/coverage-100%25-green)

# anyioutils

Utility classes and functions for AnyIO.

## Task

`task = anyioutils.create_task(my_async_func(), task_group)` behaves the same as `task = asyncio.create_task(my_async_func())` except that an existing `task_group` has to be passed for the task to be launched in the background.

You can also use `task = anyioutils.Task(my_async_func())` and then launch the `task` with `task_group.start_soon(task.wait)`, and/or await it with `result = await task.wait()`.

```py
from anyioutils import CancelledError, Task, create_task
from anyio import create_task_group, run, sleep

async def foo():
    return 1

async def bar():
    await sleep(float("inf"))

async def main():
    async with create_task_group() as tg:
        task = Task(foo())
        assert await task.wait() == 1

    try:
        async with create_task_group() as tg:
            task = create_task(bar(), tg)
            await sleep(0.1)
            task.cancel()
    except BaseExceptionGroup as exc_group:
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

## wait

`anyioutils.wait(aws, task_group)` behaves the same as `asyncio.wait(aws)` except that an existing `task_group` has to be passed.

```py
from anyioutils import ALL_COMPLETED, Task, wait
from anyio import create_task_group, run

async def foo():
    return "foo"

async def main():
    async with create_task_group() as tg:
        tasks = [Task(aw) for aw in (foo(), foo())]
        done, pending = await wait(tasks, tg, return_when=ALL_COMPLETED)
        assert done == set(tasks)
        assert not pending
        for task in done:
            assert task.result() == "foo"

run(main)
```

## Event

`anyioutils.Event` behaves the same as `asyncio.Event`.

## Queue

`anyioutils.Queue` behaves the same as `asyncio.Queue`.

## TaskGroup

`anyioutils.TaskGroup` behaves the same as `asyncio.TaskGroup`. Furthermore, when it is used, `anyioutils.create_task(coro)` won't need a task group, as one will be looked up the call stack.
