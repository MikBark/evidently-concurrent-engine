from unittest.mock import MagicMock

import pytest

from evidently_concurrent_engine import ConcurrentEngine, ConcurrentEngineFactory


@pytest.fixture
def dummy_executor():
    return MagicMock()


@pytest.fixture
def dummy_origin_engine():
    return MagicMock()


@pytest.fixture
def factory(dummy_executor, dummy_origin_engine):
    return ConcurrentEngineFactory(dummy_executor, dummy_origin_engine, timeout=300)


def test_factory_initialization(dummy_executor, dummy_origin_engine):
    factory = ConcurrentEngineFactory(dummy_executor, dummy_origin_engine, timeout=300)
    assert factory._executor is dummy_executor
    assert factory._origin_engine is dummy_origin_engine
    assert factory._timeout == 300
    assert factory._concurrent_engine is None


def test_factory_call_creates_engine(factory, dummy_executor, dummy_origin_engine):
    engine = factory()
    assert isinstance(engine, ConcurrentEngine)
    assert engine._origin_engine is dummy_origin_engine
    assert engine._executor is dummy_executor
    assert engine._finalization._timeout == 300
    assert factory._concurrent_engine is engine


def test_factory_call_returns_same_instance(factory):
    engine1 = factory()
    engine2 = factory()
    assert engine1 is engine2
