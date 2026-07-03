"""Détection des phases sur trajectoires synthétiques."""
from __future__ import annotations

import numpy as np
import pytest

from shotform.pipeline.phases import (
    PhaseSignals,
    detect_phases,
    detect_phases_from_signals,
    detect_shooting_side,
)

from .conftest import keyframes


def make_signals(
    *,
    fps: float = 30.0,
    duration: float = 4.0,
    wrist_keys=None,
) -> PhaseSignals:
    """Trajectoires synthétiques d'un tir : crouch à 1.5 s, release à 2.0 s."""
    t = np.arange(0, int(duration * fps) + 1) / fps
    wrist_keys = wrist_keys or [(0, 0.3), (1.3, 0.3), (2.0, 0.9), (2.6, 0.4), (duration, 0.4)]
    return PhaseSignals(
        t=t,
        hip_height=keyframes(t, [(0, 0.5), (1.0, 0.5), (1.5, 0.4), (2.0, 0.55),
                                 (2.2, 0.6), (2.6, 0.5), (duration, 0.5)]),
        knee_angle=keyframes(t, [(0, 170), (1.0, 170), (1.5, 110), (2.0, 175), (duration, 175)]),
        wrist_height=keyframes(t, wrist_keys),
        elbow_angle=keyframes(t, [(0, 70), (1.5, 70), (2.0, 170), (2.6, 100), (duration, 100)]),
        ankle_height=keyframes(t, [(0, 0.05), (1.9, 0.05), (2.2, 0.25), (2.6, 0.05), (duration, 0.05)]),
    )


class TestDetectFromSignals:
    def test_single_shot_phases(self):
        sig = make_signals()
        phases = detect_phases_from_signals(sig)

        assert phases.stance <= phases.crouch < phases.release <= phases.landing
        assert phases.crouch == pytest.approx(45, abs=4)      # t = 1.5 s
        assert phases.release == pytest.approx(60, abs=4)     # t = 2.0 s
        assert phases.jump_peak == pytest.approx(66, abs=4)   # t = 2.2 s
        assert 70 <= phases.landing <= 85                     # t ~ 2.5 s
        assert 20 <= phases.stance <= 40                      # fin de stabilité ~ 1.0 s
        assert not any("tirs" in w for w in phases.warnings)

    def test_two_shots_first_analyzed_and_flagged(self):
        # Deux pics de poignet séparés de 2 s = deux tirs.
        sig = make_signals(
            duration=6.0,
            wrist_keys=[(0, 0.3), (1.3, 0.3), (2.0, 0.9), (2.6, 0.3),
                        (4.0, 0.85), (4.6, 0.3), (6.0, 0.3)],
        )
        phases = detect_phases_from_signals(sig)
        assert phases.release == pytest.approx(60, abs=4)  # premier tir
        assert any("tirs détectés" in w for w in phases.warnings)

    def test_flat_wrist_raises(self):
        sig = make_signals()
        sig.wrist_height[:] = 0.5
        with pytest.raises(ValueError, match="tir"):
            detect_phases_from_signals(sig)

    def test_too_short_clip_raises(self):
        sig = make_signals()
        short = PhaseSignals(
            t=sig.t[:5], hip_height=sig.hip_height[:5], knee_angle=sig.knee_angle[:5],
            wrist_height=sig.wrist_height[:5], elbow_angle=sig.elbow_angle[:5],
            ankle_height=sig.ankle_height[:5],
        )
        with pytest.raises(ValueError, match="court"):
            detect_phases_from_signals(short)

    def test_no_jump_flagged(self):
        sig = make_signals()
        sig.ankle_height[:] = 0.05  # aucun décollage
        phases = detect_phases_from_signals(sig)
        assert any("Saut" in w or "saut" in w for w in phases.warnings)


class TestOnFullSequence:
    def test_phases_from_pose_sequence(self, shot_sequence):
        seq, truth = shot_sequence
        phases = detect_phases(seq, "right")
        assert phases.crouch == pytest.approx(truth["crouch"], abs=5)
        assert phases.release == pytest.approx(truth["release"], abs=5)
        assert phases.jump_peak == pytest.approx(truth["jump_peak"], abs=5)
        assert abs(phases.landing - truth["landing"]) <= 8
        assert phases.stance <= truth["stance"] + 5

    def test_shooting_side_auto_detection(self, shot_sequence):
        seq, _ = shot_sequence
        assert detect_shooting_side(seq) == "right"
