"""Géométrie 3D sur squelettes synthétiques connus."""
from __future__ import annotations

import numpy as np
import pytest

from shotform import landmarks as lm
from shotform.pipeline.angles import (
    METRIC_ORDER,
    angle_deg,
    angle_deg_series,
    compute_metrics,
    elbow_lateral_deg,
    elevation_deg,
    trunk_lean_deg,
)
from shotform.pipeline.phases import Phases

from .conftest import make_sequence, set_knee_angle, standing_frame


class TestAngleDeg:
    def test_right_angle(self):
        assert angle_deg([1, 0, 0], [0, 0, 0], [0, 1, 0]) == pytest.approx(90.0)

    def test_straight(self):
        assert angle_deg([-1, 0, 0], [0, 0, 0], [1, 0, 0]) == pytest.approx(180.0)

    def test_45_degrees_3d(self):
        assert angle_deg([1, 0, 0], [0, 0, 0], [1, 1, 0]) == pytest.approx(45.0)

    def test_invariant_to_rotation(self):
        """L'angle 3D ne change pas quand le squelette tourne (angle de caméra)."""
        a, b, c = np.array([1.0, 0, 0]), np.zeros(3), np.array([0.3, 0.8, 0.0])
        base = angle_deg(a, b, c)
        for theta in np.linspace(0, 2 * np.pi, 7):
            rot = np.array([
                [np.cos(theta), 0, np.sin(theta)],
                [0, 1, 0],
                [-np.sin(theta), 0, np.cos(theta)],
            ])
            assert angle_deg(rot @ a, rot @ b, rot @ c) == pytest.approx(base, abs=1e-9)

    def test_degenerate_returns_nan(self):
        assert np.isnan(angle_deg([0, 0, 0], [0, 0, 0], [1, 0, 0]))

    def test_series_matches_scalar(self):
        a = np.array([[1, 0, 0], [0, 2, 0]], dtype=float)
        b = np.zeros((2, 3))
        c = np.array([[0, 1, 0], [1, 0, 0]], dtype=float)
        out = angle_deg_series(a, b, c)
        assert out == pytest.approx([90.0, 90.0])


class TestElevationAndTrunk:
    def test_elevation_vertical(self):
        assert elevation_deg([0, 1, 0]) == pytest.approx(90.0)

    def test_elevation_horizontal(self):
        assert elevation_deg([1, 0, 0]) == pytest.approx(0.0)

    def test_elevation_45(self):
        assert elevation_deg([1, 1, 0]) == pytest.approx(45.0)

    def test_elevation_downwards_negative(self):
        assert elevation_deg([0, -1, 0]) == pytest.approx(-90.0)

    def test_trunk_vertical(self):
        assert trunk_lean_deg([0, 1.5, 0], [0, 1.0, 0]) == pytest.approx(0.0)

    def test_trunk_45(self):
        assert trunk_lean_deg([0.5, 1.5, 0], [0, 1.0, 0]) == pytest.approx(45.0)


class TestElbowLateral:
    def test_in_plane_is_zero(self):
        # Coude dans le plan vertical épaule-poignet -> pas de chicken wing.
        assert elbow_lateral_deg([0, 1.5, 0], [0.0, 1.2, 0], [0, 1.0, 0.3]) == pytest.approx(0.0, abs=1e-9)

    def test_vertical_axis_is_degenerate(self):
        # Épaule->poignet parallèle à la verticale : plan de tir indéfini -> NaN.
        shoulder = np.array([0.0, 1.5, 0.0])
        wrist = np.array([0.0, 2.5, 0.0])
        elbow = shoulder + np.array([0.5, np.sqrt(3) / 2, 0.0])
        assert np.isnan(elbow_lateral_deg(shoulder, elbow, wrist))

    def test_out_of_plane_known_angle(self):
        # Axe épaule->poignet horizontal en x ; plan de tir = plan xz... non :
        # plan contenant (1,0,0) et la verticale = plan xy, normale = z.
        shoulder = np.zeros(3)
        wrist = np.array([1.0, 0.5, 0.0])
        # coude à 30° hors du plan : distance z = sin(30°) * longueur bras (1).
        elbow = np.array([np.cos(np.radians(30)) * 0.8, 0.2, 0.5])
        expected = np.degrees(np.arcsin(0.5 / np.linalg.norm(elbow - shoulder)))
        assert elbow_lateral_deg(shoulder, elbow, wrist) == pytest.approx(expected)


class TestComputeMetrics:
    def _make_three_frame_sequence(self):
        """stance (debout), crouch (genoux 120°), release (bras levé)."""
        stance = standing_frame()

        crouch = standing_frame()
        set_knee_angle(crouch, 120.0)

        release = standing_frame()
        # Bras droit levé : coude à 90°, avant-bras vertical.
        release[lm.RIGHT_SHOULDER] = (0.2, 1.5, 0.0)
        release[lm.RIGHT_ELBOW] = (0.5, 1.5, 0.0)   # bras horizontal
        release[lm.RIGHT_WRIST] = (0.5, 1.9, 0.0)   # avant-bras vertical
        world = np.stack([stance, crouch, release])
        return make_sequence(world, fps=2.0)  # 0.5 s par frame

    def test_known_values(self):
        seq = self._make_three_frame_sequence()
        phases = Phases(stance=0, crouch=1, release=2, landing=2, jump_peak=2)
        metrics = compute_metrics(seq, phases, "right")

        assert set(metrics) == set(METRIC_ORDER)
        assert metrics["knee_flexion_shooting"].value == pytest.approx(120.0, abs=1e-6)
        assert metrics["knee_flexion_opposite"].value == pytest.approx(120.0, abs=1e-6)
        assert metrics["trunk_lean"].value == pytest.approx(0.0, abs=1e-6)
        assert metrics["elbow_angle"].value == pytest.approx(90.0, abs=1e-6)
        assert metrics["forearm_elevation"].value == pytest.approx(90.0, abs=1e-6)
        # poignet (1.9) - nez (1.7) = 0.2 ; tronc = 0.5 -> ratio 0.4
        assert metrics["release_height"].value == pytest.approx(0.4, abs=1e-6)
        assert metrics["crouch_to_release_time"].value == pytest.approx(0.5, abs=1e-9)
        assert metrics["jump_symmetry"].value == pytest.approx(0.0, abs=1e-9)

    def test_camera_rotation_leaves_angles_unchanged(self):
        """Critère phase 1 : mêmes angles quelle que soit l'orientation (3D monde)."""
        seq = self._make_three_frame_sequence()
        phases = Phases(stance=0, crouch=1, release=2, landing=2, jump_peak=2)
        base = compute_metrics(seq, phases, "right")

        theta = np.radians(40)  # vue de 3/4
        rot = np.array([
            [np.cos(theta), 0, np.sin(theta)],
            [0, 1, 0],
            [-np.sin(theta), 0, np.cos(theta)],
        ])
        rotated = seq.world @ rot.T
        seq_rot = make_sequence(rotated, fps=2.0)
        turned = compute_metrics(seq_rot, phases, "right")

        for name in METRIC_ORDER:
            if name == "crouch_to_release_time":
                continue
            assert turned[name].value == pytest.approx(base[name].value, abs=1e-6), name
