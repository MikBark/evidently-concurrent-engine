"""Provide a concurrent engine for Evidently."""

from collections.abc import Callable
from copy import deepcopy
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
from evidently_concurrent_engine.futures_finalization import FuturesFinalization

EngineDataType = TypeVar('EngineDataType')
MetricImplementationType = TypeVar('MetricImplementationType', bound=MetricImplementation)
InputDataType = TypeVar('InputDataType', bound=GenericInputData)
ResultType = TypeVar('ResultType')


class FutureMetricResult(MetricResult):
    """Represent a MetricResult containing a Future."""

    class Config:
        """Configuration for FutureMetricResult."""

        type_alias = 'evidently_concurrent_engine:metric_result:FutureMetricResult'

    future: Future


class FutureMetricImplementation(MetricImplementation):
    """Wrap a MetricImplementation to return a FutureMetricResult."""

    def __init__(self, origin: MetricImplementation | Metric, executor: Executor) -> None:
        """Initialize metric implementation.

        Parameters:
            origin : MetricImplementation | Metric
                MetricImplementation or Metric instance.
            executor : Executor
                Executor for concurrent execution.
        """
        self._origin = origin
        self._executor = executor

    def calculate(self, context: Context, data: InputData) -> FutureMetricResult:
        """Return a FutureMetricResult with an encapsulated started future.

        Parameters:
            context : Context
                Context for metric calculation.
            data : InputData
                Input data for metric calculation.

        Returns:
            FutureMetricResult
                Metric result containing a Future.
        """
        if isinstance(self._origin, MetricImplementation):
            future = self._executor.submit(
                self._origin.calculate, context=context, data=data,
            )
        else:
            future = self._executor.submit(self._origin.calculate, data=data)

        return FutureMetricResult(future=future)

    @classmethod
    def supported_engines(cls) -> tuple[type[Engine]]:
        """Return supported engines.

        Returns:
            tuple[type[Engine]]
                Tuple of supported engine types.
        """
        return (ConcurrentEngine,)


class ConcurrentEngine:
    """Evidently engine wrapper for concurrent metric calculation."""

    def __init__(
        self,
        origin_engine: Engine[MetricImplementationType, InputDataType, EngineDataType],
        executor: Executor,
        finalization: FuturesFinalization[ResultType],
    ) -> None:
        """Initialize ConcurrentEngine instance.

        Parameters:
            origin_engine : Engine[MetricImplementationType, InputDataType, EngineDataType]
                Origin engine to wrap.
            executor : Executor
                Concurrent executor (for example ThreadPoolExecutor).
            finalization: FuturesFinalization
                Futures finalization strategy.
        """
        self._origin_engine = origin_engine
        self._executor = executor
        self._finalization = finalization

        self._origin_engine.get_metric_implementation = self._future_implementation_wrap(
                self._origin_engine.get_metric_implementation,
        )

    def execute_metrics(self, context: Context, data: GenericInputData) -> None:
        """Execute Evidently metrics.

        This method uses the original engine for metric calculations, but it is
        parallelized with an encapsulated executor. The method waits until all
        futures have been executed or the timeout has expired, and then retrieves
        a result.

        Parameters:
            context : Context
                Context for metric calculation.
            data : GenericInputData
                Input data for metric calculation.
        """
        self._origin_engine.execute_metrics(context, data)
        context.metric_results = self._get_final_metric_results(context.metric_results)

    def _future_implementation_wrap(
        self, origin_method: Callable[[], MetricImplementation | None],
    ) -> Callable[[], FutureMetricImplementation | None]:
        def wrapper(metric: Metric | None) -> FutureMetricImplementation:
            """Retrieve wrapped metric implementation from the origin engine.

            This method is needed to wrap some original engine-specific MetricImplementation
            into a FutureMetricImplementation. If the engine does not have a
            MetricImplementation, wrap a Metric instance.

            Parameters:
                metric : Metric
                    Metric instance.

            Returns:
                FutureMetricImplementation
                    Metric implementation from origin engine wrapped in the future.
            """
            origin_metric_impl = origin_method(metric) or metric
            return FutureMetricImplementation(origin_metric_impl, self._executor)

        return wrapper

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

    def _get_final_metric_results(
        self, future_metric_results: dict[Metric, FutureMetricResult],
    ) -> dict[Metric, MetricResult | ErrorResult]:
        futures = [result.future for result in future_metric_results.values()]
        futures_result = self._finalization.finalize(futures)
        metric_results = {}
        for name, result in zip(
            future_metric_results.keys(), futures_result, strict=False,
        ):
            if isinstance(result, Exception):
                metric_results[name] = ErrorResult(result)
            else:
                metric_results[name] = result

        return metric_results
