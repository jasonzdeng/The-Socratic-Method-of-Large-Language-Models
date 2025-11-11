# Evaluation Harness

This package contains utilities for running regression suites on historical market events.

* `datasets.py` – data structures and helpers for loading events.
* `metrics.py` – correctness and diversity metrics.
* `runner.py` – harness orchestrating the evaluation.

To run an evaluation, implement the `Analyst` protocol and supply an iterable of `MarketEvent` instances to `EvaluationHarness.run`.
