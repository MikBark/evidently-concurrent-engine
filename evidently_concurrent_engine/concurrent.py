"""Provide protocols for concurrent execution.

This protocol allows replacement with custom executor or future classes while maintaining
compatibility with standard concurrency.future and executor classes.
"""

from collections.abc import Sequence
from typing import Callable, Generic, ParamSpec, Protocol, TypeVar, runtime_checkable

ResultType_co = TypeVar('ResultType_co', covariant=True)
ResultType = TypeVar('ResultType')
P = ParamSpec('P')


@runtime_checkable
class Future(Protocol, Generic[ResultType_co]):
    """Provide a protocol for Future objects.

    Provide a protocol for Future objects, compatible with concurrent.futures.Future,
    including only essential methods.
    """

    def exception(self, timeout: float | int | None = None) -> Exception | None:
        """Return the exception raised by the call that the future represents.

        Parameters:
            timeout : float, int, None
                Number of seconds to wait for the exception if the future isn't done.
                If None, there is no limit on the wait time. Default None.

        Return:
            Exception, None
                Exception raised by the call or None if the call completed without
                raising some exception.

        Raises:
            concurrent.futures.CancelledError
                If the future was cancelled.
            TimeoutError | concurrent.futures.TimeoutError
                If the future didn't finish executing before the given timeout.
        """

    def result(self, timeout: float | int | None = None) -> ResultType_co:
        """Return the result of the call that the future represents.

        Parameters:
            timeout : float, int, None
                Number of seconds to wait for the result if the future isn't done.
                If None, there is no limit on the wait time. Default None.

        Return:
            ResultType_co
                Result of the call.

        Raises:
            concurrent.futures.CancelledError
                If the future was cancelled.
            TimeoutError | concurrent.futures.TimeoutError
                If the future didn't finish executing before the given timeout.
            Exception
                Any exception raised by the call.
        """


class Executor(Protocol):
    """Provide a protocol for Executor objects.

    Provide a protocol for Executor objects, compatible with concurrent.futures.Future,
    including only essential methods.
    """

    def submit(
        self, fn: Callable[P, ResultType], *args: P.args, **kwargs: P.kwargs,
    ) -> Future[ResultType]:
        """Submit a callable to be executed with the given arguments.

        Parameters:
            fn : Callable[P, ResultType]
                Callable to execute.
            args : P.args
                Positional arguments for the callable.
            kwargs : P.kwargs
                Keyword arguments for the callable.

        Return:
            Future[ResultType]
                Future representing the execution of the callable.
        """


class FuturesFinalization(Protocol, Generic[ResultType]):
    """Define a protocol for finalizing multiple futures."""

    def finalize(
        self, futures: Sequence[Future[ResultType]],
    ) -> Sequence[ResultType | Exception]:
        """Wait for and retrieve results or exceptions from a sequence of futures.

        Parameters:
            futures : Sequence[Future[ResultType]]
                Ordered sequence of futures to finalize.

        Returns:
            Sequence[ResultType | Exception]
                Ordered sequence of result or exceptions of futures execution.
        """
