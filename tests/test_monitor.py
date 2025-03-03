import time

import pytest

from anyio import create_task_group, sleep
from anyioutils import Monitor


pytestmark = pytest.mark.anyio

async def test_busy():

    period = 0.01
    block = 0.05

    async def busy_task():
        while True:
            time.sleep(block)
            await sleep(0)

    async with Monitor(period) as monitor:
        async with create_task_group() as tg:
            tg.start_soon(busy_task)
            await sleep(period * 100)
            tg.cancel_scope.cancel()

    assert  (block / period) < monitor.result < (block / period) * 15


async def test_not_busy():

    period = 0.01

    async with create_task_group() as tg:
        monitor = Monitor(period)
        tg.start_soon(monitor.run)
        await sleep(period * 100)
        tg.cancel_scope.cancel()

    assert  1 < monitor.result < 4
