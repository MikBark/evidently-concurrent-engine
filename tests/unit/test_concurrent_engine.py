from unittest.mock import MagicMock

import pytest
from evidently.base_metric import ErrorResult

from evidently_concurrent_engine.engine import (
    ConcurrentEngine,
    FutureMetricImplementation,
    FutureMetricResult,
)


@pytest.fixture
def dummy_executor():
    exec_mock = MagicMock()
    exec_mock.submit = MagicMock(side_effect=lambda func, **kw: MagicMock())
    return exec_mock


@pytest.fixture
def dummy_finalization():
    final_mock = MagicMock()
    final_mock.finalize = MagicMock()
    return final_mock


@pytest.fixture
def dummy_origin_engine():
    return MagicMock()


@pytest.fixture
def dummy_metric():
    return object()


@pytest.fixture
def dummy_context():
    ctx = type('DummyContext', (), {})()
    ctx.metric_results = {}
    return ctx


@pytest.fixture
def dummy_input_data():
    return object()


def test_get_metric_implementation_valid(
    dummy_executor, dummy_finalization, dummy_origin_engine, dummy_metric
):
    dummy_impl = MagicMock()
    dummy_origin_engine.get_metric_implementation.return_value = dummy_impl
    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, dummy_finalization)
    fmi = ce.get_metric_implementation(dummy_metric)
    assert isinstance(fmi, FutureMetricImplementation)
    assert fmi._origin is dummy_impl
    assert fmi._executor is dummy_executor


def test_get_metric_implementation_fallback(
    dummy_executor, dummy_finalization, dummy_origin_engine, dummy_metric
):
    dummy_origin_engine.get_metric_implementation.return_value = None
    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, dummy_finalization)
    fmi = ce.get_metric_implementation(dummy_metric)
    assert isinstance(fmi, FutureMetricImplementation)
    assert fmi._origin is dummy_metric


def test_execute_metrics_success(
    dummy_executor,
    dummy_finalization,
    dummy_origin_engine,
    dummy_context,
    dummy_input_data,
    dummy_metric,
):
    dummy_future = MagicMock()
    fmr = FutureMetricResult(future=dummy_future)

    def fake_execute(ctx, data):
        ctx.metric_results = {dummy_metric: fmr}

    dummy_origin_engine.execute_metrics.side_effect = fake_execute
    dummy_finalization.finalize.return_value = [100]
    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, dummy_finalization)
    ce.execute_metrics(dummy_context, dummy_input_data)
    assert dummy_context.metric_results == {dummy_metric: 100}


def test_execute_metrics_exception(
    dummy_executor,
    dummy_finalization,
    dummy_origin_engine,
    dummy_context,
    dummy_input_data,
    dummy_metric,
):
    dummy_future = MagicMock()
    fmr = FutureMetricResult(future=dummy_future)

    def fake_execute(ctx, data):
        ctx.metric_results = {dummy_metric: fmr}

    dummy_origin_engine.execute_metrics.side_effect = fake_execute
    dummy_exc = Exception('calculation failed')
    dummy_finalization.finalize.return_value = [dummy_exc]
    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, dummy_finalization)
    ce.execute_metrics(dummy_context, dummy_input_data)
    res = dummy_context.metric_results[dummy_metric]
    assert isinstance(res, ErrorResult)
    assert res.exception.args == dummy_exc.args


def test_attribute_delegation(dummy_executor, dummy_finalization, dummy_origin_engine):
    dummy_origin_engine.dummy_attr = 'test_value'
    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, dummy_finalization)
    assert ce.dummy_attr == 'test_value'


def test_get_final_metric_results_mixed(dummy_executor, dummy_finalization):
    m1 = object()
    m2 = object()
    f1 = MagicMock()
    f2 = MagicMock()
    fmr1 = FutureMetricResult(future=f1)
    fmr2 = FutureMetricResult(future=f2)
    dummy_finalization.finalize.return_value = [42, Exception('error occurred')]
    ce = ConcurrentEngine(MagicMock(), dummy_executor, dummy_finalization)
    results = ce._get_final_metric_results({m1: fmr1, m2: fmr2})
    assert results[m1] == 42
    res = results[m2]
    assert isinstance(res, ErrorResult)
    assert res.exception.args == ('error occurred',)
