from anyio import create_task_group, sleep
from time import monotonic


class Monitor:
    def __init__(self, period: float = 0.01):
        self._period = period
        self._result = 0
        self._iter = 1

    async def __aenter__(self) -> "Monitor":
        self._task_group = create_task_group()
        tg = await self._task_group.__aenter__()
        tg.start_soon(self._run)
        self._cancel_scope = tg.cancel_scope
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        self._cancel_scope.cancel()
        await self._task_group.__aexit__(None, None, None)

    async def _run(self):
        while True:
            t0 = monotonic()
            await sleep(self._period)
            t1 = monotonic()
            factor = (t1 - t0) / self._period
            self._result = self._result + (factor - self._result) / self._iter
            self._iter += 1

    @property
    def result(self) -> float:
        return self._result
