# Version history

## 0.7.2

- When `Task` is cancelled, close coroutine if not started.

## 0.7.1

- Add `Task` exception handler.

## 0.7.0

- Add documentation.
- Make `start_task` not async.
- Make `wait` accept futures.

## 0.6.6

- Add `start_task()`.
- Allow `Monitor` to be used without a context manager.
- Test PyPy v3.11.

## 0.6.5

- Improve typing of `start_guest_run()`.

## 0.6.4

- Add guest mode.
- Add monitor.

## 0.6.3

- Add `TaskGroup.cancel_scope`.
- Add task name.

## 0.6.2

- Fix `Event.clear`.

## 0.6.1

- Raise callback exceptions.

## 0.6.0

- Add `Event`.
- Add `TaskGroup` and make `create_task(coro)` use current `TaskGroup` by default.
- Fix `add_done_callback`.
- Add `Future` and `Task` generic type.

## 0.5.0

- Add `Queue`.
- Don't raise exception when cancelling by default.

## 0.4.11

- Ignore any error while sending stream.

## 0.4.9

- Fix types.

## 0.4.8

- Add `wait()`.

## 0.4.7

- Add PyPI trusted publishing.
- When running coverage, don't run tests again.

## 0.4.6

- Move `trio` to test dependencies.

## 0.4.5

- Add `py.typed` marker.

## 0.4.4

- Add `future.cancel(raise_exception=False)`.

## 0.4.3

- Fix future being awaited multiple times.

## 0.4.2

- Fix task being awaited multiple times.

## 0.4.1

- Add `task.cancel(raise_exception=False)`.

## 0.4.0

- Launch task in `create_task()`, passing an external task group.

## 0.3.0

- Fix `Task`.

## 0.2.0

- Add `Task` and `create_task`.

## 0.1.0

- Add CI.

## 0.0.0
