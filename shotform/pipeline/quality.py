"""Qualité de la mesure : orientation caméra et confiance par métrique.

Le rapport final distingue toujours mesure fiable / mesure incertaine :
une métrique dont les landmarks sont mal vus (bras masqué, tireur de dos,
détection perdue) est marquée « faible confiance » plutôt que de produire
un chiffre faux.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .. import landmarks as lm
from .angles import METRIC_ORDER

# Seuil de visibilité MediaPipe en dessous duquel un landmark est jugé mal vu.
VISIBILITY_THRESHOLD = 0.5
# Au-delà de cet angle (° par rapport à la vue de face), le tireur est de profil.
PROFILE_ANGLE = 65.0

RECOMMENDED_SETUP = (
    "Filmez de trois quarts face, côté bras de tir, caméra à hauteur de "
    "poitrine, à 3-5 m du tireur, corps entier visible du début à la fin."
)


@dataclass
class MetricConfidence:
    confidence: float  # [0, 1]
    reliable: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class QualityReport:
    view_angle_deg: float       # 0 = face/dos, 90 = profil
    orientation: str            # "face" | "trois-quarts" | "profil" | "dos" | "inconnue"
    facing_camera: bool
    detection_rate: float
    per_metric: dict[str, MetricConfidence]
    warnings: list[str] = field(default_factory=list)
    recommendation: str | None = None


# Landmarks dont dépend chaque métrique, par côté ("side" = côté tir,
# "opp" = côté opposé, sinon index absolu).
_METRIC_LANDMARKS: dict[str, list] = {
    "knee_flexion_shooting": [("side", "hip"), ("side", "knee"), ("side", "ankle")],
    "knee_flexion_opposite": [("opp", "hip"), ("opp", "knee"), ("opp", "ankle")],
    "trunk_lean": [lm.LEFT_SHOULDER, lm.RIGHT_SHOULDER, lm.LEFT_HIP, lm.RIGHT_HIP],
    "elbow_angle": [("side", "shoulder"), ("side", "elbow"), ("side", "wrist")],
    "forearm_elevation": [("side", "elbow"), ("side", "wrist")],
    "body_alignment": [("side", "shoulder"), ("side", "hip"), ("side", "knee")],
    "elbow_lateral_offset": [("side", "shoulder"), ("side", "elbow"), ("side", "wrist")],
    "release_height": [("side", "wrist"), lm.NOSE, lm.LEFT_HIP, lm.RIGHT_HIP],
    "crouch_to_release_time": [("side", "knee"), ("side", "wrist")],
    "jump_symmetry": [lm.LEFT_ANKLE, lm.RIGHT_ANKLE],
}

# Phase à laquelle chaque métrique est mesurée (fenêtre de visibilité).
_METRIC_PHASE_ATTR = {
    "knee_flexion_shooting": "crouch",
    "knee_flexion_opposite": "crouch",
    "trunk_lean": "crouch",
    "elbow_angle": "release",
    "forearm_elevation": "release",
    "body_alignment": "release",
    "elbow_lateral_offset": "release",
    "release_height": "release",
    "crouch_to_release_time": "release",
    "jump_symmetry": "jump_peak",
}

# Métriques qui dépendent du bras de tir (dégradées si le bras est masqué
# ou si le tireur est de dos / de profil côté opposé).
_ARM_METRICS = {
    "elbow_angle",
    "forearm_elevation",
    "elbow_lateral_offset",
    "release_height",
}


def _resolve_indices(spec: list, shooting_side: str) -> list[int]:
    side = lm.side_landmarks(shooting_side)
    opp = lm.side_landmarks(lm.opposite_side(shooting_side))
    out = []
    for item in spec:
        if isinstance(item, tuple):
            group, joint = item
            out.append(side[joint] if group == "side" else opp[joint])
        else:
            out.append(item)
    return out


def estimate_view_angle(seq, frame: int) -> tuple[float, bool]:
    """Orientation du tireur vs caméra, via le vecteur épaule gauche->droite.

    Renvoie (angle en degrés, facing_camera). 0° = plan frontal (face ou dos),
    90° = profil. `facing_camera` distingue face/dos : le nez est plus proche
    de la caméra (z monde plus petit) que le milieu des épaules quand le
    tireur fait face à l'objectif.
    """
    w = seq.world[frame]
    shoulder_vec = w[lm.RIGHT_SHOULDER] - w[lm.LEFT_SHOULDER]
    dx, dz = shoulder_vec[0], shoulder_vec[2]
    if not np.isfinite(dx) or not np.isfinite(dz) or (abs(dx) + abs(dz)) < 1e-9:
        return float("nan"), True
    view = float(np.degrees(np.arctan2(abs(dz), abs(dx))))
    mid_shoulder_z = (w[lm.LEFT_SHOULDER][2] + w[lm.RIGHT_SHOULDER][2]) / 2
    facing = bool(w[lm.NOSE][2] <= mid_shoulder_z) if np.isfinite(w[lm.NOSE][2]) else True
    return view, facing


def orientation_label(view_angle: float, facing: bool) -> str:
    if not np.isfinite(view_angle):
        return "inconnue"
    if not facing and view_angle < PROFILE_ANGLE:
        return "dos"
    if view_angle < 25.0:
        return "face"
    if view_angle < PROFILE_ANGLE:
        return "trois-quarts"
    return "profil"


def assess_quality(seq, phases, metrics, shooting_side: str) -> QualityReport:
    """Évalue la confiance de chaque métrique à sa phase de mesure."""
    view_angle, facing = estimate_view_angle(seq, phases.release)
    orientation = orientation_label(view_angle, facing)
    half_win = max(1, int(round(0.1 * seq.fps)))

    per_metric: dict[str, MetricConfidence] = {}
    for name in METRIC_ORDER:
        idx = _resolve_indices(_METRIC_LANDMARKS[name], shooting_side)
        frame = getattr(phases, _METRIC_PHASE_ATTR[name])
        lo, hi = max(0, frame - half_win), min(len(seq), frame + half_win + 1)
        vis_win = seq.visibility[lo:hi][:, idx]
        confidence = float(np.nanmin(np.nanmean(vis_win, axis=0), initial=1.0))
        reasons: list[str] = []

        if not seq.present[lo:hi].any():
            confidence = 0.0
            reasons.append("détection perdue au moment de la mesure")
        if confidence < VISIBILITY_THRESHOLD:
            reasons.append("landmarks concernés mal vus (visibilité basse)")
        if orientation == "dos":
            confidence = min(confidence, 0.3)
            reasons.append("tireur de dos : mesure très incertaine")
        elif orientation == "profil" and name in _ARM_METRICS:
            # De profil, le bras de tir peut être occulté par le corps ;
            # on ne dégrade que si la visibilité le confirme partiellement.
            if confidence < 0.75:
                confidence = min(confidence, 0.45)
                reasons.append("profil : bras de tir potentiellement masqué")

        value = metrics[name].value if name in metrics else float("nan")
        if not np.isfinite(value):
            confidence = 0.0
            reasons.append("valeur non calculable (landmarks manquants)")

        per_metric[name] = MetricConfidence(
            confidence=round(confidence, 3),
            reliable=confidence >= VISIBILITY_THRESHOLD,
            reasons=reasons,
        )

    report = QualityReport(
        view_angle_deg=round(view_angle, 1) if np.isfinite(view_angle) else float("nan"),
        orientation=orientation,
        facing_camera=facing,
        detection_rate=round(seq.detection_rate(), 3),
        per_metric=per_metric,
    )
    unreliable = [n for n, c in per_metric.items() if not c.reliable]
    if orientation == "dos":
        report.warnings.append("Le tireur est filmé de dos : analyse peu fiable.")
    if unreliable:
        report.warnings.append(
            "Métriques incertaines exclues du score : "
            + ", ".join(unreliable)
        )
        report.recommendation = RECOMMENDED_SETUP
    return report
