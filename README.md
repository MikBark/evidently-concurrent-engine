# Evidently Concurrent Engine

A concurrent execution engine for [Evidently](https://github.com/evidentlyai/evidently) metrics calculations, designed to improve performance on large datasets and multiple metrics.

## Installation

```bash
pip install evidently_concurrent_engine
```

**Dependencies**: Python >= 3.9, evidently >= 0.4.38

## Quick Start

```python
import pandas as pd
from evidently.metrics import DatasetSummaryMetric, ColumnDistributionMetric
from evidently.report import Report
from evidently_concurrent_engine import ConcurrentEngineFactory

data = pd.DataFrame({
    'feature_1': [1, 2, 3] * 1000,
    'feature_2': [0.1, 0.2, 0.3] * 1000,
})

engine_factory = ConcurrentEngineFactory()

report = Report(metrics=[
    DatasetSummaryMetric(),
    ColumnDistributionMetric('feature_1'),
    ColumnDistributionMetric('feature_2'),
])
report.run(current_data=data, engine=engine_factory)

# View results
print(report.as_dataframe())
```

## Configuration

### Executor Options

```python
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=8)

factory = ConcurrentEngineFactory(executor=executor)
```

**Note**: ProcessPoolExecutor is not currently supported. Use ThreadPoolExecutor for concurrent execution.

### Timeout

```python
# Default: 600 seconds (10 minutes)
factory = ConcurrentEngineFactory(timeout=600)

# Custom timeout
factory = ConcurrentEngineFactory(timeout=300)
```

## Performance

| Scenario | Speedup |
|-----------|----------|
| Multiple metrics (10+) | 3-5x |
| Large datasets (>100k rows) | 2-4x |
| Many columns (50+) | 4-6x |

**Benchmarks**: 20 column metrics on 100k rows
- Sequential: ~12 seconds
- Concurrent (8 threads): ~3 seconds (~4x faster)

## When to Use

**Use for**:
- 50+ metrics
- Datasets > 10k rows
- Independent metrics
- Production batch evaluations

**Avoid for**:
- 1-2 metrics (overhead > benefit)
- Very small datasets (<1k rows)
- Single-core systems
- Real-time streaming
