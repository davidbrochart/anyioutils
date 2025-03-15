import pytest

from anyio import fail_after, get_cancelled_exc_class, sleep, wait_all_tasks_blocked
from anyioutils import TaskGroup, create_task, wait

pytestmark = pytest.mark.anyio


async def test_task_group():
    async def coro(res):
        return res

    async def foo():
        tasks = [create_task(coro(2)), create_task(coro(3))]
        return await wait(tasks)

    async with TaskGroup() as tg:
        task0 = tg.create_task(coro(0))
        task1 = tg.create_task(coro(1))
        task2 = tg.create_task(foo())

    assert task0.result() == 0
    assert task1.result() == 1
    done, pending = task2.result()
    assert not pending
    assert sum([task.result() for task in done]) == 5


async def test_task_group_cancel():
    async def coro():
        await sleep(float("inf"))

    async with TaskGroup() as tg:
        task0 = tg.create_task(coro())
        tg.cancel_scope.cancel()

    with pytest.raises(get_cancelled_exc_class()):
        await task0.wait()


async def test_task_group_background_task():
    async def coro():
        await sleep(float("inf"))

    with fail_after(1):
        async with TaskGroup() as tg:
            task0 = tg.create_task(coro(), background=True)
            await wait_all_tasks_blocked()
