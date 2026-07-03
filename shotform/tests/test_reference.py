"""Agrégation du référentiel."""
from __future__ import annotations

import numpy as np
import pytest

from shotform.pipeline.angles import METRIC_ORDER
from shotform.reference.build_reference import MIN_SAMPLES, aggregate_samples


class TestAggregateSamples:
    def test_median_and_percentiles(self):
        values = [90.0, 92.0, 94.0, 96.0, 98.0, 100.0]
        samples = {"elbow_angle": values}
        out = aggregate_samples(samples, {"elbow_angle": "°"})
        m = out["elbow_angle"]
        assert m["median"] == pytest.approx(95.0)
        assert m["p10"] == pytest.approx(np.percentile(values, 10))
        assert m["p90"] == pytest.approx(np.percentile(values, 90))
        assert m["n"] == 6
        assert m["reliable"] is True
        assert m["unit"] == "°"

    def test_too_few_samples_marked_unreliable(self):
        samples = {"elbow_angle": [90.0] * (MIN_SAMPLES - 1)}
        out = aggregate_samples(samples, {})
        assert out["elbow_angle"]["reliable"] is False
        assert out["elbow_angle"]["n"] == MIN_SAMPLES - 1

    def test_empty_and_nan_samples(self):
        samples = {"elbow_angle": [float("nan"), float("inf")]}
        out = aggregate_samples(samples, {})
        m = out["elbow_angle"]
        assert m["n"] == 0
        assert m["median"] is None
        assert m["reliable"] is False

    def test_all_metrics_present_in_output(self):
        out = aggregate_samples({}, {})
        assert set(out) == set(METRIC_ORDER)
