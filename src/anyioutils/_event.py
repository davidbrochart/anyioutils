from anyio import Event as _Event


class Event:
    """
    An event object. Not thread-safe.

    An event can be used to notify multiple tasks that some event has happened.

    An Event object manages an internal flag that can be set to `True` with the [set()][anyioutils.Event.set] method and reset to `False` with the [clear()][anyioutils.Event.clear] method. The [wait()][anyioutils.Event.wait] method blocks until the flag is set to `True`. The flag is set to `False` initially.
    """
    def __init__(self) -> None:
        self._event = _Event()

    async def wait(self) -> bool:
        """
        Wait until the event is set.

        Returns:
            If the event is set, return `True` immediately. Otherwise block until another task calls [set()][anyioutils.Event.set].
        """
        await self._event.wait()
        return True

    def set(self) -> None:
        """
        Set the event.

        All tasks waiting for event to be set will be immediately awakened.
        """
        self._event.set()

    def is_set(self) -> bool:
        """
        Returns:
            `True` if the event is set.
        """
        return self._event.is_set()

    def clear(self) -> None:
        """
        Clear (unset) the event.

        Tasks awaiting on [wait()][anyioutils.Event.wait] will now block until the [set()][anyioutils.Event.set] method is called again.
        """
        if self._event.is_set():
            self._event = _Event()
