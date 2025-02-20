"""This module contains a simple implementation of the FuturesFinalization protocol."""

import concurrent
from collections.abc import Iterable
from math import inf
from time import time
from typing import TypeVar

from evidently_concurrent_engine.concurrent import Future, FuturesFinalization

ResultType = TypeVar('ResultType')


class TimeoutFuturesFinalization(FuturesFinalization[ResultType]):
    """Wait for all futures with a timeout and return their results or exceptions."""

    def __init__(self, timeout: float | int = inf) -> None:
        """Initialize the FuturesResult with a timeout.

        Parameters:
            timeout : float, int
                Maximum time to wait for all futures in seconds. After this, all
                unfinished futures are closed. Default is infinity.
        """
        self._timeout = timeout

    def finalize(
        self, futures: Iterable[Future[ResultType]],
    ) -> list[ResultType | Exception]:
        """Wait for all futures and collect their results or exceptions.

        Parameters:
            futures : Iterable[Future[ResultType]]
                An iterable of Future objects to wait for.

        Returns:
            list[ResultType, Exception]
                A list containing the results or exceptions from each future.
        """
        rest_of_time = self._timeout
        result = []
        for future in futures:
            start_time = time()
            result.append(self._wait_single(future, max(rest_of_time, 0)))
            rest_of_time -= time() - start_time

        return result

    def _wait_single(
        self, future: Future[ResultType], timeout: float | int,
    ) -> ResultType | Exception:
        """Wait for a single future and return its result or exception.

        Parameters:
            future : Future[ResultType]
                The future to wait for.
            timeout : float, int
                The timeout in seconds to wait for the future.

        Returns:
            ResultType, Exception
                The result of the future or an exception if it occurred.
        """
        try:
            exception = future.exception(timeout=timeout)
        # We need to check both TimeoutError and concurrent.futures.TimeoutError,
        # because in Python <3.11, this is not an alias.
        except (
            TimeoutError,
            concurrent.futures.TimeoutError,
            concurrent.futures.CancelledError,
        ) as e:
            exception = e

        return future.result(timeout=0) if exception is None else exception
