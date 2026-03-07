import concurrent.futures
from unittest.mock import MagicMock, patch

import pytest
from evidently.base_metric import ErrorResult
from evidently.calculation_engine.metric_implementation import MetricImplementation

from evidently_concurrent_engine.engine import (
    ConcurrentEngine,
    FutureMetricImplementation,
    FutureMetricResult,
)


@pytest.fixture
def dummy_executor():
    """Mock executor fixture."""
    return MagicMock()


@pytest.fixture
def dummy_origin_engine():
    """Mock origin engine fixture."""
    engine = MagicMock()
    engine.get_metric_implementation = MagicMock(return_value=None)
    return engine


@pytest.fixture
def dummy_metric():
    """Mock metric fixture."""
    return MagicMock()


@pytest.fixture
def dummy_context():
    """Mock context fixture."""
    ctx = MagicMock()
    ctx.metric_results = {}
    return ctx


@pytest.fixture
def dummy_input_data():
    """Mock input data fixture."""
    return MagicMock()


def test_future_metric_result_wait_success():
    """Success path: wait() returns the resolved metric result."""
    mock_future = MagicMock()
    mock_future.exception.return_value = None
    mock_future.result.return_value = MagicMock(value=42)

    fmr = FutureMetricResult(
        future=mock_future,
        timeout=100,
        start_time=0,
    )
    result = fmr.wait()
    assert result.value == 42


def test_future_metric_result_wait_with_exception():
    """Exception path: wait() returns an ErrorResult when exception() provides a value."""
    mock_future = MagicMock()
    mock_future.exception.return_value = ValueError('calculation failed')

    fmr = FutureMetricResult(
        future=mock_future,
        timeout=100,
        start_time=0,
    )
    result = fmr.wait()
    assert isinstance(result, ErrorResult)
    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == 'calculation failed'


def test_future_metric_result_wait_timeout():
    """Timeout path: wait() returns an ErrorResult and cancels the future."""
    mock_future = MagicMock()
    mock_future.exception.side_effect = concurrent.futures.TimeoutError
    mock_future.cancel = MagicMock()

    fmr = FutureMetricResult(
        future=mock_future,
        timeout=100,
        start_time=0,
    )
    result = fmr.wait()
    assert isinstance(result, ErrorResult)
    assert isinstance(result.exception, concurrent.futures.TimeoutError)
    mock_future.cancel.assert_called_once()


def test_future_metric_result_wait_cancelled():
    """Cancelled path: wait() returns an ErrorResult when future is cancelled."""
    mock_future = MagicMock()
    mock_future.exception.side_effect = concurrent.futures.CancelledError
    mock_future.cancel = MagicMock()

    fmr = FutureMetricResult(
        future=mock_future,
        timeout=100,
        start_time=0,
    )
    result = fmr.wait()
    assert isinstance(result, ErrorResult)
    assert isinstance(result.exception, concurrent.futures.CancelledError)
    mock_future.cancel.assert_called_once()


def test_future_metric_implementation_with_metric_implementation(dummy_executor):
    """Wrapper around MetricImplementation returns a FutureMetricResult."""
    origin_impl = MagicMock(spec=MetricImplementation)
    origin_impl.calculate = MagicMock()
    mock_future = MagicMock()
    dummy_executor.submit = MagicMock(return_value=mock_future)

    with patch('evidently_concurrent_engine.engine.time', return_value=100.0):
        fmi = FutureMetricImplementation(origin_impl, dummy_executor, timeout=60)
        result = fmi.calculate(MagicMock(), MagicMock())

    assert isinstance(result, FutureMetricResult)
    assert result.timeout == 60
    assert result.start_time == 100.0
    dummy_executor.submit.assert_called_once()


def test_future_metric_implementation_with_metric(dummy_executor):
    """Wrapper around Metric returns a FutureMetricResult."""
    origin_metric = MagicMock()
    origin_metric.calculate = MagicMock()
    mock_future = MagicMock()
    dummy_executor.submit = MagicMock(return_value=mock_future)

    with patch('evidently_concurrent_engine.engine.time', return_value=100.0):
        fmi = FutureMetricImplementation(origin_metric, dummy_executor, timeout=60)
        result = fmi.calculate(MagicMock(), MagicMock())

    assert isinstance(result, FutureMetricResult)
    dummy_executor.submit.assert_called_once()


def test_get_metric_implementation_wraps_correctly(
    dummy_executor, dummy_origin_engine, dummy_metric
):
    """Test that get_metric_implementation is wrapped correctly during execute_metrics."""
    dummy_impl = MagicMock()
    dummy_origin_engine.get_metric_implementation = MagicMock(return_value=dummy_impl)

    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, timeout=60)

    # Before execute_metrics, get_metric_implementation should
    # still be the original method
    assert ce.get_metric_implementation is dummy_origin_engine.get_metric_implementation

    # Create a simple execute scenario
    ctx = MagicMock()
    ctx.metric_results = {}
    dummy_origin_engine.execute_metrics = MagicMock()

    ce.execute_metrics(ctx, MagicMock())

    # After execute_metrics, get_metric_implementation should be restored
    assert ce.get_metric_implementation is dummy_origin_engine.get_metric_implementation


def test_execute_metrics_uses_wrapped_implementation(
    dummy_executor, dummy_origin_engine, dummy_context, dummy_input_data, dummy_metric
):
    """Test that during execute_metrics, the wrapped implementation is used."""
    dummy_impl = MagicMock(spec=MetricImplementation)
    dummy_impl.calculate = MagicMock(return_value=MagicMock())
    dummy_origin_engine.get_metric_implementation = MagicMock(return_value=dummy_impl)

    mock_future = MagicMock()
    mock_future.exception.return_value = None
    mock_result = MagicMock()
    mock_future.result.return_value = mock_result
    dummy_executor.submit = MagicMock(return_value=mock_future)

    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, timeout=60)

    def fake_execute(ctx, data):
        # Inside execute_metrics, get_metric_implementation should be wrapped
        wrapped = ce.get_metric_implementation(dummy_metric)
        assert isinstance(wrapped, FutureMetricImplementation)
        assert wrapped._executor is dummy_executor
        assert wrapped._timeout == 60

        # Simulate the engine setting metric_results
        fmr = FutureMetricResult(future=mock_future, timeout=60, start_time=0)
        ctx.metric_results = {dummy_metric: fmr}

    dummy_origin_engine.execute_metrics.side_effect = fake_execute
    ce.execute_metrics(dummy_context, dummy_input_data)

    assert dummy_context.metric_results == {dummy_metric: mock_result}


def test_execute_metrics_patches_and_restores(
    dummy_executor, dummy_origin_engine, dummy_context, dummy_input_data
):
    """
    Test get_metric_implementation patching.

    During execute_metrics, verify that the get_metric_implementation
    method is properly patched and then restored.
    """
    original_method = dummy_origin_engine.get_metric_implementation
    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, timeout=60)

    def fake_execute(ctx, data):
        ctx.metric_results = {}

    dummy_origin_engine.execute_metrics.side_effect = fake_execute
    ce.execute_metrics(dummy_context, dummy_input_data)

    assert dummy_origin_engine.get_metric_implementation is original_method


def test_execute_metrics_success(
    dummy_executor, dummy_origin_engine, dummy_context, dummy_input_data, dummy_metric
):
    """Test that on success, the metric result is placed into context metric_results."""
    mock_future = MagicMock()
    mock_future.exception.return_value = None
    mock_result = MagicMock()
    mock_future.result.return_value = mock_result
    dummy_executor.submit = MagicMock(return_value=mock_future)

    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, timeout=60)

    def fake_execute(ctx, data):
        fmr = FutureMetricResult(future=mock_future, timeout=60, start_time=0)
        ctx.metric_results = {dummy_metric: fmr}

    dummy_origin_engine.execute_metrics.side_effect = fake_execute
    ce.execute_metrics(dummy_context, dummy_input_data)

    assert dummy_context.metric_results == {dummy_metric: mock_result}


def test_execute_metrics_exception(
    dummy_executor, dummy_origin_engine, dummy_context, dummy_input_data, dummy_metric
):
    """Test exception path when execute_metrics encounters a failed future."""
    mock_future = MagicMock()
    mock_future.exception.return_value = ValueError('calculation failed')
    dummy_executor.submit = MagicMock(return_value=mock_future)

    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, timeout=60)

    def fake_execute(ctx, data):
        fmr = FutureMetricResult(future=mock_future, timeout=60, start_time=0)
        ctx.metric_results = {dummy_metric: fmr}

    dummy_origin_engine.execute_metrics.side_effect = fake_execute
    ce.execute_metrics(dummy_context, dummy_input_data)

    res = dummy_context.metric_results[dummy_metric]
    assert isinstance(res, ErrorResult)
    assert isinstance(res.exception, ValueError)
    assert str(res.exception) == 'calculation failed'


def test_attribute_delegation(dummy_executor, dummy_origin_engine):
    """Attribute delegation passes through to the origin engine."""
    dummy_origin_engine.dummy_attr = 'test_value'
    ce = ConcurrentEngine(dummy_origin_engine, dummy_executor, timeout=60)
    assert ce.dummy_attr == 'test_value'


def test_supported_engines():
    """Ensure FutureMetricImplementation reports supported engines correctly."""
    assert FutureMetricImplementation.supported_engines() == (ConcurrentEngine,)
