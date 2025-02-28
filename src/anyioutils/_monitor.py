from anyio import create_task_group, sleep
from time import monotonic


class Monitor:
    def __init__(self, period: float = 0.01):
        """
        Create a Monitor with a [run()][anyioutils.Monitor.run] method that runs a task in the background and measures how saturated the event-loop is.
        This can also be used to detect (long) blocking calls in the event-loop.


        The Monitor can be used as an async context manager, in which case it will automatically run, or by launching its [run()][anyioutils.Monitor.run]
        method in the backgroup manually.

        Args:
            period: The period in seconds to make the measurement.
        """
        self._period = period
        self._result = 0
        self._iter = 1

    async def __aenter__(self) -> "Monitor":
        self._task_group = create_task_group()
        tg = await self._task_group.__aenter__()
        tg.start_soon(self.run)
        self._cancel_scope = tg.cancel_scope
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        self._cancel_scope.cancel()
        await self._task_group.__aexit__(None, None, None)

    async def run(self):
        """
        Run the Monitor. This has to be run in the background.
        """
        while True:
            t0 = monotonic()
            await sleep(self._period)
            t1 = monotonic()
            factor = (t1 - t0) / self._period
            self._result = self._result + (factor - self._result) / self._iter
            self._iter += 1

    @property
    def result(self) -> float:
        """
        The result of the measurement (greater than `1`). The closer to `1`, the less saturated the event-loop is. The greater, the more saturated the event-loop is.
        """
        return self._result
