"""Provide a factory for creating ConcurrentEngine instances."""

from concurrent.futures import ThreadPoolExecutor

from evidently.calculation_engine.engine import Engine
from evidently.calculation_engine.python_engine import PythonEngine

from evidently_concurrent_engine.concurrent import Executor
from evidently_concurrent_engine.engine import ConcurrentEngine

DEFAULT_ORIGIN_ENGINE = PythonEngine()
DEFAULT_EXECUTOR = ThreadPoolExecutor()


class ConcurrentEngineFactory:
    """Factory for simple ConcurrentEngine integration with the Evidently library.

    Report.run need the class of Engine subclass. We need throw some parametrs to the
    Engine constructor. Thats why we need pass factory insted Engine class. Insted of
    this we can use partial or something else callable with the predefined params.
    """

    def __init__(
        self,
        executor: Executor = DEFAULT_EXECUTOR,
        origin_engine: Engine = DEFAULT_ORIGIN_ENGINE,
        timeout: int = 600,
    ) -> None:
        """Initialize the ConcurrentEngineFactory instance.

        Parameters:
            executor : Executor
            origin_engine : Engine
            timeout : int
        """
        self._executor = executor
        self._origin_engine = origin_engine
        self._timeout = timeout

        self._concurrent_engine: ConcurrentEngine | None = None

    def __call__(self) -> ConcurrentEngine:
        """Retrieve ConcurrentEngine instance.

        On the first call, create a ConcurrentEngine instance with encapsulated
        parameters. On every next call, retrieve an existing instance.

        Returns:
            ConcurrentEngine
        """
        if self._concurrent_engine is None:
            self._concurrent_engine = ConcurrentEngine(
                origin_engine=self._origin_engine,
                executor=self._executor,
                timeout=self._timeout,
            )

        return self._concurrent_engine
