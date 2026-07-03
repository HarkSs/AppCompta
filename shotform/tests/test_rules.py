"""Moteur de règles : statuts, score, conseils français."""
from __future__ import annotations

import json

import pytest

from shotform.pipeline.angles import METRIC_LABELS, Metric
from shotform.pipeline.quality import MetricConfidence
from shotform.verdict import messages
from shotform.verdict.rules import (
    FALLBACK_PATH,
    WEIGHTS,
    evaluate,
    load_reference,
    metric_score,
    summary_text,
)


def _metric(name: str, value: float, unit: str = "°", phase: str = "release") -> Metric:
    return Metric(name, value, unit, phase, METRIC_LABELS[name])


def _confidences(names, reliable=True, reasons=None):
    return {
        n: MetricConfidence(confidence=0.9 if reliable else 0.2,
                            reliable=reliable, reasons=reasons or [])
        for n in names
    }


class TestMetricScore:
    def test_inside_range_is_good(self):
        status, score, dev, direction = metric_score(95.0, 85.0, 100.0)
        assert (status, score, dev, direction) == ("bon", 100.0, 0.0, "in")

    def test_slightly_above_is_borderline(self):
        status, score, dev, direction = metric_score(102.0, 85.0, 100.0)
        assert status == "limite"
        assert direction == "high"
        assert dev == pytest.approx(2.0)
        assert 60.0 <= score < 100.0

    def test_far_below_is_to_fix(self):
        status, score, dev, direction = metric_score(60.0, 85.0, 100.0)
        assert status == "a_corriger"
        assert direction == "low"
        assert 0.0 <= score < 60.0

    def test_score_monotonic_in_deviation(self):
        scores = [metric_score(v, 85.0, 100.0)[1] for v in (100, 103, 106, 112, 130)]
        assert scores == sorted(scores, reverse=True)


class TestEvaluate:
    def test_fallback_reference_loaded_and_flagged(self):
        ref = load_reference()
        assert FALLBACK_PATH.is_file()
        assert ref["type"] == "fallback"

        metrics = {"elbow_angle": _metric("elbow_angle", 93.0)}
        verdict = evaluate(metrics, _confidences(["elbow_angle"]))
        assert verdict.reference_type == "fallback"
        assert any("repli" in n for n in verdict.notices)
        assert verdict.items[0].status == "bon"
        assert verdict.score == 100.0

    def test_bad_elbow_gets_french_advice_with_numbers(self):
        metrics = {"elbow_angle": _metric("elbow_angle", 112.0)}
        verdict = evaluate(metrics, _confidences(["elbow_angle"]))
        item = verdict.items[0]
        assert item.status == "a_corriger"
        assert "112°" in item.message
        assert "85°" in item.message and "100°" in item.message
        assert "coude" in item.message

    def test_unreliable_metric_excluded_from_score(self):
        metrics = {
            "elbow_angle": _metric("elbow_angle", 93.0),
            "jump_symmetry": _metric("jump_symmetry", 0.5, unit="×tronc", phase="timing"),
        }
        conf = _confidences(["elbow_angle"])
        conf.update(_confidences(["jump_symmetry"], reliable=False, reasons=["bras masqué"]))
        verdict = evaluate(metrics, conf)
        assert "jump_symmetry" in verdict.excluded
        # jump_symmetry (0.5, très mauvais) exclu -> score reste 100.
        assert verdict.score == 100.0
        incertain = [i for i in verdict.items if i.metric == "jump_symmetry"][0]
        assert incertain.status == "incertain"

    def test_weighted_score(self):
        # elbow bon (100), jump_symmetry catastrophique (score 0) :
        # score = (3*100 + 0.5*0) / 3.5.
        metrics = {
            "elbow_angle": _metric("elbow_angle", 93.0),
            "jump_symmetry": _metric("jump_symmetry", 5.0, unit="×tronc", phase="timing"),
        }
        verdict = evaluate(metrics, _confidences(metrics.keys()))
        expected = (WEIGHTS["elbow_angle"] * 100.0) / (
            WEIGHTS["elbow_angle"] + WEIGHTS["jump_symmetry"]
        )
        assert verdict.score == pytest.approx(expected, abs=0.1)

    def test_no_reliable_metric_no_score(self):
        metrics = {"elbow_angle": _metric("elbow_angle", 93.0)}
        verdict = evaluate(metrics, _confidences(["elbow_angle"], reliable=False))
        assert verdict.score is None
        assert any("score" in n.lower() for n in verdict.notices)

    def test_custom_reference_missing_metric(self):
        ref = {"type": "pro", "metrics": {}}
        metrics = {"elbow_angle": _metric("elbow_angle", 93.0)}
        verdict = evaluate(metrics, _confidences(["elbow_angle"]), reference=ref)
        assert verdict.items[0].status == "sans_reference"
        assert verdict.score is None


class TestSummaryAndMessages:
    def test_summary_text_readable(self):
        metrics = {
            "elbow_angle": _metric("elbow_angle", 112.0),
            "trunk_lean": _metric("trunk_lean", 12.0, phase="crouch"),
        }
        verdict = evaluate(metrics, _confidences(metrics.keys()))
        text = summary_text(verdict, phases_times={"release": 1.2})
        assert "Score global" in text
        assert "release à 1.20 s" in text
        assert "[À corriger]" in text
        assert "[Bon]" in text

    def test_all_metrics_have_advice_templates(self):
        from shotform.pipeline.angles import METRIC_ORDER

        for name in METRIC_ORDER:
            assert name in messages.ADVICE, name
            assert set(messages.ADVICE[name]) == {"low", "high"}

    def test_fallback_json_covers_all_metrics(self):
        from shotform.pipeline.angles import METRIC_ORDER

        ref = json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))
        for name in METRIC_ORDER:
            m = ref["metrics"][name]
            assert m["p10"] < m["p90"], name
