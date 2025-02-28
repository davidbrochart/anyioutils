import pytest
from anyioutils import ALL_COMPLETED, FIRST_COMPLETED, FIRST_EXCEPTION, Task, create_task, wait
from anyio import create_task_group, sleep

pytestmark = pytest.mark.anyio


async def foo(wait: float = 0, raise_exception: bool = False) -> str:
    await sleep(wait)
    if raise_exception:
        raise RuntimeError("foo")
    return "foo"


async def test_wait_all_completed() -> None:
    async with create_task_group() as tg:
        tasks = [Task(aw) for aw in (foo(), foo())]
        done, pending = await wait(tasks, tg, return_when=ALL_COMPLETED)
        assert done == set(tasks)
        assert not pending
        for task in done:
            assert task.result() == "foo"


async def test_wait_first_completed() -> None:
    async with create_task_group() as tg:
        tasks = [Task(aw) for aw in (foo(), foo(wait=0.1))]
        done, pending = await wait(tasks, tg, return_when=FIRST_COMPLETED)
        assert len(done) == 1
        assert len(pending) == 1
        assert done == set([tasks[0]]) 
        assert pending == set([tasks[1]]) 
        for task in done:
            assert task.result() == "foo"
        for task in pending:
            assert await task.wait() == "foo"


async def test_wait_first_exception() -> None:
    async with create_task_group() as tg:
        tasks = [Task(aw) for aw in (foo(raise_exception=True), foo(wait=0.1))]
        done, pending = await wait(tasks, tg, return_when=FIRST_EXCEPTION)
        assert len(done) == 1
        assert len(pending) == 1
        assert done == set([tasks[0]]) 
        assert pending == set([tasks[1]]) 
        for task in done:
            with pytest.raises(RuntimeError) as excinfo:
                task.result()
            assert str(excinfo.value) == "foo"
        for task in pending:
            assert await task.wait() == "foo"


async def test_wait_not_tasks() -> None:
    async with create_task_group() as tg:
        aw = foo()
        with pytest.raises(TypeError) as excinfo:
            done, pending = await wait([aw], tg)
        assert str(excinfo.value) == "Pass tasks or futures, not <class 'coroutine'>"
        await aw
