"""Provide a concurrent engine for Evidently."""

import concurrent
from collections.abc import Callable
from time import time
from typing import Any, TypeVar

from evidently.base_metric import (
    ErrorResult,
    GenericInputData,
    InputData,
    Metric,
    MetricResult,
)
from evidently.calculation_engine.engine import Engine
from evidently.calculation_engine.metric_implementation import (
    MetricImplementation,
)
from evidently.suite.base_suite import Context

from evidently_concurrent_engine.concurrent import Executor, Future

EngineDataType = TypeVar('EngineDataType')
MetricImplementationType = TypeVar('MetricImplementationType', bound=MetricImplementation)
InputDataType = TypeVar('InputDataType', bound=GenericInputData)
AnyMetricResult = MetricResult | ErrorResult


class FutureMetricResult(MetricResult):
    """Represent a `MetricResult` containing a `Future` with timeout handling."""

    class Config:
        """Configuration for FutureMetricResult."""

        type_alias = 'evidently_concurrent_engine:metric_result:FutureMetricResult'

    future: Future[AnyMetricResult]
    timeout: float | int
    start_time: float | int

    def wait(self) -> AnyMetricResult:
        """Wait for the future to complete within the timeout and return the result.

        Returns:
            The resolved MetricResult or an ErrorResult if an exception occurs or timeout
            is reached.
        """
        rest_of_time = max(self.timeout - (time() - self.start_time), 0)

        try:
            exception = self.future.exception(timeout=rest_of_time)
        except (concurrent.futures.TimeoutError, concurrent.futures.CancelledError) as e:
            exception = e
            self.future.cancel()

        if exception is None:
            return self.future.result(timeout=0)

        return ErrorResult(exception)


class FutureMetricImplementation(MetricImplementation):
    """Wrap a MetricImplementation to return a `FutureMetricResult`."""

    def __init__(
        self,
        origin: MetricImplementation | Metric,
        executor: Executor,
        timeout: float | int,
    ) -> None:
        """Initialize metric implementation.

        Parameters:
            origin : MetricImplementation | Metric
                Original `MetricImplementation` or `Metric` instance.
            executor : Executor
                Executor for concurrent execution.
        """
        self._origin = origin
        self._executor = executor
        self._timeout = timeout

    def calculate(self, context: Context, data: InputData) -> FutureMetricResult:
        """Return a FutureMetricResult with an encapsulated started future.

        Parameters:
            context : Context
                Context for metric calculation.
            data : InputData
                Input data for metric calculation.

        Returns:
            FutureMetricResult
                Metric result containing a `Future`.
        """
        if isinstance(self._origin, MetricImplementation):
            future = self._executor.submit(
                self._origin.calculate,
                context=context,
                data=data,
            )
        else:
            future = self._executor.submit(self._origin.calculate, data=data)
        return FutureMetricResult(future=future, timeout=self._timeout, start_time=time())

    @classmethod
    def supported_engines(cls) -> tuple[type[Engine]]:
        """Return supported engines.

        Returns:
            tuple[type[Engine]]
                Tuple of supported engine types.
        """
        return (ConcurrentEngine,)


class ConcurrentEngine:
    """Evidently engine wrapper for concurrent metric calculation.

    The class patches the `get_metric_implementation` method with a wrapper to return
    `FutureMetricImplementation` instances.
    """

    def __init__(
        self,
        origin_engine: Engine[MetricImplementationType, InputDataType, EngineDataType],
        executor: Executor,
        timeout: int | float,
    ) -> None:
        """Initialize `ConcurrentEngine` instance.

        Parameters:
            origin_engine : Engine[
                MetricImplementationType, InputDataType, EngineDataType
            ]
                Origin engine to wrap.
            executor : Executor
                Concurrent executor (for example ThreadPoolExecutor).
            timeout : int | float
                Timeout of metrics execution.
        """
        self._origin_engine = origin_engine
        self._executor = executor
        self._timeout = timeout

    def execute_metrics(self, context: Context, data: GenericInputData) -> None:
        """Execute Evidently metrics.

        This method uses the original engine for metric calculations, but it is
        parallelized with an encapsulated executor. The method waits until all
        futures have been executed or the timeout has expired, and then finish execution.

        Parameters:
            context : Context
                Context for metric calculation.
            data : GenericInputData
                Input data for metric calculation.
        """
        engine = self._origin_engine
        method_backup = engine.get_metric_implementation
        engine.get_metric_implementation = self._future_implementation_wrap(method_backup)
        engine.execute_metrics(context, data)
        engine.get_metric_implementation = method_backup

        context.metric_results = {
            metric: result.wait() for metric, result in context.metric_results.items()
        }

    def __getattr__(self, name: str) -> Any:
        """Proxy calls to the encapsulated origin engine.

        Parameters:
            name : str
                Name of the attribute.

        Returns:
            Any
                Some origin engine attribute.
        """
        return getattr(self._origin_engine, name)

    def _future_implementation_wrap(
        self,
        origin_method: Callable[[], MetricImplementation | None],
    ) -> Callable[[], FutureMetricImplementation | None]:
        def wrapper(metric: Metric | None) -> FutureMetricImplementation:
            """Retrieve wrapped metric implementation from the origin engine.

            This method is needed to wrap some original engine-specific
            `MetricImplementation` into a `FutureMetricImplementation`. If the engine does
            not have a `MetricImplementation`, wrap a Metric instance.

            Parameters:
                metric : Metric
                    Metric instance.

            Returns:
                FutureMetricImplementation
                    Metric implementation from origin engine wrapped in the future.
            """
            origin_metric_impl = origin_method(metric) or metric
            return FutureMetricImplementation(
                origin_metric_impl, self._executor, self._timeout
            )

        return wrapper
