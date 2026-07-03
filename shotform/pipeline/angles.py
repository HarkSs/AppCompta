"""Calcul des angles 3D par phase, à partir des world landmarks.

Toute la géométrie est faite en 3D (mètres, repère hanches, Y vers le haut) :
les angles articulaires sont ainsi quasi invariants au point de vue de la
caméra. Seule la « verticale » suppose une caméra à peu près horizontale
(limite documentée dans le README).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .. import landmarks as lm

# ---------------------------------------------------------------------------
# Géométrie de base (testée sur squelettes synthétiques)
# ---------------------------------------------------------------------------

UP = np.array([0.0, 1.0, 0.0])  # verticale du repère interne (Y vers le haut)


def angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle en degrés au point b, formé par les segments b->a et b->c."""
    v1 = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    v2 = np.asarray(c, dtype=float) - np.asarray(b, dtype=float)
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 <= 1e-12 or n2 <= 1e-12:
        return float("nan")
    cos = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos)))


def angle_deg_series(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Version vectorisée de angle_deg sur des trajectoires (T, 3)."""
    v1 = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    v2 = np.asarray(c, dtype=float) - np.asarray(b, dtype=float)
    n1 = np.linalg.norm(v1, axis=-1)
    n2 = np.linalg.norm(v2, axis=-1)
    denom = n1 * n2
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = np.clip(np.einsum("...i,...i", v1, v2) / denom, -1.0, 1.0)
        out = np.degrees(np.arccos(cos))
    out = np.where(denom <= 1e-12, np.nan, out)
    return out


def elevation_deg(v: np.ndarray) -> float:
    """Angle d'un vecteur au-dessus du plan horizontal (négatif = vers le bas)."""
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    if n <= 1e-12:
        return float("nan")
    return float(np.degrees(np.arcsin(np.clip(np.dot(v, UP) / n, -1.0, 1.0))))


def trunk_lean_deg(shoulder_center: np.ndarray, hip_center: np.ndarray) -> float:
    """Inclinaison du tronc (hanches->épaules) par rapport à la verticale."""
    v = np.asarray(shoulder_center, dtype=float) - np.asarray(hip_center, dtype=float)
    n = np.linalg.norm(v)
    if n <= 1e-12:
        return float("nan")
    cos = np.clip(np.dot(v, UP) / n, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos)))


def elbow_lateral_deg(shoulder: np.ndarray, elbow: np.ndarray, wrist: np.ndarray) -> float:
    """Écart latéral du coude ("chicken wing") en degrés.

    Le plan de tir idéal contient l'axe épaule->poignet et la verticale.
    On mesure l'angle d'élévation du coude HORS de ce plan :
    asin(distance du coude au plan / longueur du bras épaule->coude).
    0° = coude parfaitement dans le plan de tir.
    """
    s = np.asarray(shoulder, dtype=float)
    e = np.asarray(elbow, dtype=float)
    w = np.asarray(wrist, dtype=float)
    sw = w - s
    normal = np.cross(sw, UP)
    n_norm = np.linalg.norm(normal)
    upper = np.linalg.norm(e - s)
    if n_norm <= 1e-12 or upper <= 1e-12:
        return float("nan")
    dist = abs(np.dot(e - s, normal / n_norm))
    return float(np.degrees(np.arcsin(np.clip(dist / upper, 0.0, 1.0))))


def torso_length(world_frame: np.ndarray) -> float:
    """Longueur du tronc (centre épaules -> centre hanches), en mètres."""
    sc = (world_frame[lm.LEFT_SHOULDER] + world_frame[lm.RIGHT_SHOULDER]) / 2
    hc = (world_frame[lm.LEFT_HIP] + world_frame[lm.RIGHT_HIP]) / 2
    return float(np.linalg.norm(sc - hc))


# ---------------------------------------------------------------------------
# Métriques par phase
# ---------------------------------------------------------------------------


@dataclass
class Metric:
    name: str
    value: float
    unit: str
    phase: str  # "crouch" | "release" | "timing"
    label: str  # libellé français pour les rapports


# Ordre canonique des métriques (partagé avec quality, reference et verdict).
METRIC_ORDER = (
    "knee_flexion_shooting",
    "knee_flexion_opposite",
    "trunk_lean",
    "elbow_angle",
    "forearm_elevation",
    "body_alignment",
    "elbow_lateral_offset",
    "release_height",
    "crouch_to_release_time",
    "jump_symmetry",
)

METRIC_LABELS = {
    "knee_flexion_shooting": "Flexion du genou (côté tir) à la crouch",
    "knee_flexion_opposite": "Flexion du genou (côté opposé) à la crouch",
    "trunk_lean": "Inclinaison du tronc à la crouch",
    "elbow_angle": "Angle du coude de tir à la release",
    "forearm_elevation": "Élévation de l'avant-bras à la release",
    "body_alignment": "Alignement épaule-hanche-genou à la release",
    "elbow_lateral_offset": "Écart latéral du coude à la release",
    "release_height": "Hauteur relative de release",
    "crouch_to_release_time": "Durée crouch → release",
    "jump_symmetry": "Symétrie du saut",
}


def compute_metrics(seq, phases, shooting_side: str) -> dict[str, Metric]:
    """Calcule toutes les métriques 3D aux frames de phase détectées.

    `seq` : PoseSequence ; `phases` : Phases. Les valeurs non calculables
    (landmarks manquants) valent NaN et seront écartées par le module quality.
    """
    side = lm.side_landmarks(shooting_side)
    opp = lm.side_landmarks(lm.opposite_side(shooting_side))
    w_crouch = seq.world[phases.crouch]
    w_release = seq.world[phases.release]

    metrics: dict[str, Metric] = {}

    def add(name: str, value: float, unit: str, phase: str) -> None:
        metrics[name] = Metric(name, float(value), unit, phase, METRIC_LABELS[name])

    # --- Crouch ---
    add(
        "knee_flexion_shooting",
        angle_deg(w_crouch[side["hip"]], w_crouch[side["knee"]], w_crouch[side["ankle"]]),
        "°", "crouch",
    )
    add(
        "knee_flexion_opposite",
        angle_deg(w_crouch[opp["hip"]], w_crouch[opp["knee"]], w_crouch[opp["ankle"]]),
        "°", "crouch",
    )
    sc = (w_crouch[lm.LEFT_SHOULDER] + w_crouch[lm.RIGHT_SHOULDER]) / 2
    hc = (w_crouch[lm.LEFT_HIP] + w_crouch[lm.RIGHT_HIP]) / 2
    add("trunk_lean", trunk_lean_deg(sc, hc), "°", "crouch")

    # --- Release ---
    add(
        "elbow_angle",
        angle_deg(w_release[side["shoulder"]], w_release[side["elbow"]], w_release[side["wrist"]]),
        "°", "release",
    )
    add(
        "forearm_elevation",
        elevation_deg(w_release[side["wrist"]] - w_release[side["elbow"]]),
        "°", "release",
    )
    add(
        "body_alignment",
        angle_deg(w_release[side["shoulder"]], w_release[side["hip"]], w_release[side["knee"]]),
        "°", "release",
    )
    add(
        "elbow_lateral_offset",
        elbow_lateral_deg(w_release[side["shoulder"]], w_release[side["elbow"]], w_release[side["wrist"]]),
        "°", "release",
    )
    torso = torso_length(w_release)
    if torso > 1e-9:
        rel_h = (w_release[side["wrist"]][1] - w_release[lm.NOSE][1]) / torso
    else:
        rel_h = float("nan")
    add("release_height", rel_h, "×tronc", "release")

    # --- Timing ---
    add(
        "crouch_to_release_time",
        seq.timestamps[phases.release] - seq.timestamps[phases.crouch],
        "s", "timing",
    )
    w_peak = seq.world[phases.jump_peak]
    torso_p = torso_length(w_peak)
    if torso_p > 1e-9:
        sym = abs(w_peak[lm.LEFT_ANKLE][1] - w_peak[lm.RIGHT_ANKLE][1]) / torso_p
    else:
        sym = float("nan")
    add("jump_symmetry", sym, "×tronc", "timing")

    return metrics
