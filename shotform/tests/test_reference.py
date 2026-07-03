"""Agrégation du référentiel et garde-fous de plausibilité."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from shotform.pipeline.angles import METRIC_LABELS, Metric
from shotform.pipeline.angles import METRIC_ORDER
from shotform.reference.build_reference import (
    MIN_SAMPLES,
    aggregate_samples,
    shot_plausibility_issues,
)


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


class TestShotPlausibility:
    def _analysis(self, release_height: float, forearm_elevation: float):
        def m(name, value):
            return Metric(name, value, "°", "release", METRIC_LABELS[name])

        return SimpleNamespace(metrics={
            "release_height": m("release_height", release_height),
            "forearm_elevation": m("forearm_elevation", forearm_elevation),
        })

    def test_real_shot_passes(self):
        assert shot_plausibility_issues(self._analysis(0.4, 60.0)) == []

    def test_wrist_below_head_rejected(self):
        issues = shot_plausibility_issues(self._analysis(-0.8, 60.0))
        assert any("poignet" in i for i in issues)

    def test_downward_forearm_rejected(self):
        issues = shot_plausibility_issues(self._analysis(0.4, -30.0))
        assert any("avant-bras" in i for i in issues)

    def test_nan_values_do_not_reject(self):
        assert shot_plausibility_issues(self._analysis(float("nan"), float("nan"))) == []
