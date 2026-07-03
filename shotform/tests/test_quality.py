"""Confiance des mesures et estimation de l'angle de caméra."""
from __future__ import annotations

import numpy as np

from shotform import landmarks as lm
from shotform.pipeline.angles import compute_metrics
from shotform.pipeline.phases import Phases, detect_phases
from shotform.pipeline.quality import (
    assess_quality,
    estimate_view_angle,
    orientation_label,
)

from .conftest import make_sequence, standing_frame


def _rotated_sequence(theta_deg: float, n: int = 12):
    """Squelette debout tourné de theta autour de la verticale (0 = face caméra)."""
    theta = np.radians(theta_deg)
    rot = np.array([
        [np.cos(theta), 0, np.sin(theta)],
        [0, 1, 0],
        [-np.sin(theta), 0, np.cos(theta)],
    ])
    frame = standing_frame() @ rot.T
    world = np.repeat(frame[None], n, axis=0)
    return make_sequence(world)


class TestViewAngle:
    def test_facing_camera(self):
        seq = _rotated_sequence(0.0)
        angle, facing = estimate_view_angle(seq, 0)
        assert angle < 10
        assert facing
        assert orientation_label(angle, facing) == "face"

    def test_three_quarter(self):
        seq = _rotated_sequence(40.0)
        angle, facing = estimate_view_angle(seq, 0)
        assert orientation_label(angle, facing) == "trois-quarts"

    def test_profile(self):
        seq = _rotated_sequence(85.0)
        angle, _ = estimate_view_angle(seq, 0)
        assert angle > 65
        assert orientation_label(angle, True) == "profil"

    def test_back_to_camera(self):
        seq = _rotated_sequence(180.0)
        angle, facing = estimate_view_angle(seq, 0)
        assert not facing
        assert orientation_label(angle, facing) == "dos"


class TestPerMetricConfidence:
    def _phases(self, n: int = 12) -> Phases:
        return Phases(stance=1, crouch=3, release=6, landing=9, jump_peak=8)

    def test_all_visible_all_reliable(self):
        seq = _rotated_sequence(0.0)
        phases = self._phases()
        metrics = compute_metrics(seq, phases, "right")
        report = assess_quality(seq, phases, metrics, "right")
        # trunk/genoux : squelette debout bien vu -> fiables
        assert report.per_metric["knee_flexion_shooting"].reliable
        assert report.per_metric["trunk_lean"].reliable
        assert report.recommendation is None or "elbow" not in str(report.per_metric)

    def test_hidden_arm_flagged_unreliable(self):
        seq = _rotated_sequence(0.0)
        # Bras de tir mal vu autour de la release.
        for idx in (lm.RIGHT_SHOULDER, lm.RIGHT_ELBOW, lm.RIGHT_WRIST):
            seq.visibility[:, idx] = 0.2
        phases = self._phases()
        metrics = compute_metrics(seq, phases, "right")
        report = assess_quality(seq, phases, metrics, "right")

        elbow = report.per_metric["elbow_angle"]
        assert not elbow.reliable
        assert elbow.reasons
        # ... et une recommandation de prise de vue est émise.
        assert report.recommendation is not None
        # Le genou opposé (gauche), bien vu, reste fiable.
        assert report.per_metric["knee_flexion_opposite"].reliable

    def test_back_orientation_degrades_everything(self):
        seq = _rotated_sequence(180.0)
        phases = self._phases()
        metrics = compute_metrics(seq, phases, "right")
        report = assess_quality(seq, phases, metrics, "right")
        assert report.orientation == "dos"
        assert not report.per_metric["elbow_angle"].reliable
        assert any("dos" in w for w in report.warnings)

    def test_full_shot_sequence_reliable(self, shot_sequence):
        seq, _ = shot_sequence
        phases = detect_phases(seq, "right")
        metrics = compute_metrics(seq, phases, "right")
        report = assess_quality(seq, phases, metrics, "right")
        assert report.orientation == "face"
        assert all(c.reliable for c in report.per_metric.values())
