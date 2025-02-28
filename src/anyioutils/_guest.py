from __future__ import annotations

import inspect
from typing import Awaitable, Callable, Literal, TypeVar

import outcome

RetT = TypeVar("RetT")


def start_guest_run(
    async_fn: Callable[..., Awaitable[RetT]],
    *,
    run_sync_soon_threadsafe: Callable[[Callable[[], object]], object],
    done_callback: Callable[[outcome.Outcome[RetT]], object],
    run_sync_soon_not_threadsafe: Callable[[Callable[[], object]], object] | None = None,
    backend: Literal["asyncio"] | Literal["trio"] = "asyncio",
) -> None:
    """
    See Trio's [guest mode](https://trio.readthedocs.io/en/stable/reference-lowlevel.html#using-guest-mode-to-run-trio-on-top-of-other-event-loops).
    """
    if not inspect.iscoroutinefunction(async_fn):
        raise RuntimeError(f"Expected a coroutine function, got: {async_fn}")

    if backend == "asyncio":
        import aioguest

        aioguest.start_guest_run(
            async_fn(),
            run_sync_soon_threadsafe=run_sync_soon_threadsafe,
            done_callback=done_callback,
            run_sync_soon_not_threadsafe=run_sync_soon_not_threadsafe,
        )
    elif backend == "trio":
        import trio

        trio.lowlevel.start_guest_run(
            async_fn,
            run_sync_soon_threadsafe=run_sync_soon_threadsafe,
            done_callback=done_callback,
            run_sync_soon_not_threadsafe=run_sync_soon_not_threadsafe,
        )
    else:
        raise RuntimeError(f'Backend not supported: "{backend}"')
