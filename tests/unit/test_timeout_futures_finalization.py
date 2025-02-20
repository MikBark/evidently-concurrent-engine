import concurrent
from unittest.mock import MagicMock

import pytest

from evidently_concurrent_engine.concurrent import Future
from evidently_concurrent_engine.futures_finalization import TimeoutFuturesFinalization


@pytest.fixture
def mock_future():
    return MagicMock(spec=Future)


@pytest.fixture
def finalizer():
    return TimeoutFuturesFinalization()


def test_successful_future(finalizer, mock_future):
    """Should return the result when the future completes successfully."""
    mock_future.exception.return_value = None
    mock_future.result.return_value = 42
    result = finalizer.finalize([mock_future])
    assert result == [42]


def test_future_with_exception(finalizer, mock_future):
    """Should return the exception when the future raises an error."""
    mock_future.exception.return_value = ValueError('error')
    result = finalizer.finalize([mock_future])
    assert isinstance(result[0], ValueError)
    assert str(result[0]) == 'error'


def test_future_timeout(finalizer, mock_future):
    """Should return concurrent.futures.TimeoutError when the future does not complete."""
    mock_future.exception.side_effect = concurrent.futures.TimeoutError
    result = finalizer.finalize([mock_future])
    assert isinstance(result[0], concurrent.futures.TimeoutError)


def test_future_cancelled(finalizer, mock_future):
    """Should return concurrent.futures.CancelledError when the future is cancelled."""
    mock_future.exception.side_effect = concurrent.futures.CancelledError
    result = finalizer.finalize([mock_future])
    assert isinstance(result[0], concurrent.futures.CancelledError)


def test_multiple_futures(finalizer, mock_future):
    """Should return results in order for multiple futures."""
    mock_future1 = MagicMock(spec=Future)
    mock_future2 = MagicMock(spec=Future)
    mock_future1.exception.return_value = None
    mock_future2.exception.return_value = None
    mock_future1.result.return_value = 'a'
    mock_future2.result.return_value = 'b'
    result = finalizer.finalize([mock_future1, mock_future2])
    assert result == ['a', 'b']


def test_mixed_futures(finalizer, mock_future):
    """Should return correct results and exceptions for mixed futures."""
    mock_future1 = MagicMock(spec=Future)
    mock_future2 = MagicMock(spec=Future)
    mock_future3 = MagicMock(spec=Future)
    mock_future1.exception.return_value = None
    mock_future2.exception.return_value = RuntimeError('failure')
    mock_future3.exception.side_effect = concurrent.futures.TimeoutError
    mock_future1.result.return_value = 'success'
    result = finalizer.finalize([mock_future1, mock_future2, mock_future3])
    assert result[0] == 'success'
    assert isinstance(result[1], RuntimeError)
    assert str(result[1]) == 'failure'
    assert isinstance(result[2], concurrent.futures.TimeoutError)


def test_timeout_propagation(finalizer):
    """Should reduce the timeout across multiple futures correctly."""
    mock_future1 = MagicMock(spec=Future)
    mock_future2 = MagicMock(spec=Future)
    mock_future1.exception.return_value = None
    mock_future2.exception.side_effect = concurrent.futures.TimeoutError
    mock_future1.result.return_value = 'delayed'
    finalizer = TimeoutFuturesFinalization(1)
    result = finalizer.finalize([mock_future1, mock_future2])
    assert result[0] == 'delayed'
    assert isinstance(result[1], concurrent.futures.TimeoutError)
