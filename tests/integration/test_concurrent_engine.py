from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pytest
from evidently import ColumnMapping
from evidently.metrics import (
    ColumnCorrelationsMetric,
    ColumnDistributionMetric,
    ColumnSummaryMetric,
    DatasetMissingValuesMetric,
    DatasetSummaryMetric,
)
from evidently.report import Report
from evidently.test_preset import DataQualityTestPreset
from evidently.test_suite import TestSuite

from evidently_concurrent_engine.factory import ConcurrentEngineFactory


@pytest.fixture
def default_data():
    return pd.DataFrame({
        'col1': [1, 2, 3] * 10,
        'col2': [0.1, 0.2, 0.3] * 10,
        'col3': ['a', 'b', 'c'] * 10,
        'target': [1, 0] * 15,
    })


@pytest.fixture
def default_column_mapping():
    return ColumnMapping(
        target='target',
        numerical_features=['col1', 'col2'],
        categorical_features=['col3'],
    )


@pytest.fixture
def default_concurrent_engine_facory():
    return ConcurrentEngineFactory(ThreadPoolExecutor())


@pytest.mark.parametrize(
        'metrics', [
            [DatasetSummaryMetric()],
            [DatasetMissingValuesMetric()],
            [ColumnSummaryMetric(col) for col in ['col1', 'col2', 'col3']],
            [ColumnDistributionMetric(col) for col in ['col1', 'col2', 'col3']],
            [ColumnCorrelationsMetric(col) for col in ['col1', 'col2', 'col3']],
        ]
)
def test_concurrent_engine_metric_report_run(
    metrics, default_data, default_column_mapping, default_concurrent_engine_facory,
):
    report = Report(metrics=metrics)
    report.run(
        current_data=default_data,
        reference_data=None,
        column_mapping=default_column_mapping,
        engine=default_concurrent_engine_facory,
    )
    result = report.as_dataframe()


def test_concurrent_engine_test_suite_run(
    default_data, default_column_mapping, default_concurrent_engine_facory,
):
    test_suite = TestSuite(tests=[DataQualityTestPreset()])
    test_suite.run(
        current_data=default_data,
        reference_data=None,
        column_mapping=default_column_mapping,
        engine=default_concurrent_engine_facory,
    )
    test_suite.json()
