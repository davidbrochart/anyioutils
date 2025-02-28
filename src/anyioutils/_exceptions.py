class CancelledError(BaseException):
    """
    The operation has been cancelled.
    """


class InvalidStateError(BaseException):
    """
    Invalid internal state of [Task][anyioutils.Task] or [Future][anyioutils.Future].

    Can be raised in situations like setting a result value for a Future object that already has a result value set.
    """
