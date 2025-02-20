"""TODO: this module provide concurrent evidently engine implementation.

Concurrent engine work with the python stdlib concurrency.future compleated protocol (more
in concurrent_engine.concurrent)
"""

from evidently_concurrent_engine.concurrent import Executor, Future
from evidently_concurrent_engine.engine import ConcurrentEngine
from evidently_concurrent_engine.factory import ConcurrentEngineFactory

__all__ = [
    'ConcurrentEngine',
    'ConcurrentEngineFactory',
    'Executor',
    'Future',
]
