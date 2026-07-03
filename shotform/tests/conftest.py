"""Fabriques de squelettes et de séquences synthétiques pour les tests."""
from __future__ import annotations

import numpy as np
import pytest

from shotform import landmarks as lm
from shotform.pipeline.extractor import PoseSequence


def keyframes(t: np.ndarray, keys: list[tuple[float, float]]) -> np.ndarray:
    times, values = zip(*keys)
    return np.interp(t, times, values)


def standing_frame() -> np.ndarray:
    """Squelette debout, bras le long du corps, connu et symétrique.

    Repère : mètres, Y vers le haut, personnage dans le plan XY (z=0),
    nez légèrement vers la caméra (z négatif) pour l'orientation « face ».
    """
    f = np.zeros((lm.NUM_LANDMARKS, 3))
    f[lm.NOSE] = (0.0, 1.7, -0.05)
    for i in range(1, 11):  # yeux/oreilles/bouche : proches du nez
        f[i] = (0.0, 1.68, -0.04)
    f[lm.LEFT_SHOULDER] = (-0.2, 1.5, 0.0)
    f[lm.RIGHT_SHOULDER] = (0.2, 1.5, 0.0)
    f[lm.LEFT_ELBOW] = (-0.25, 1.25, 0.0)
    f[lm.RIGHT_ELBOW] = (0.25, 1.25, 0.0)
    f[lm.LEFT_WRIST] = (-0.25, 1.0, 0.0)
    f[lm.RIGHT_WRIST] = (0.25, 1.0, 0.0)
    for w, extra in ((lm.LEFT_WRIST, (lm.LEFT_PINKY, lm.LEFT_INDEX, lm.LEFT_THUMB)),
                     (lm.RIGHT_WRIST, (lm.RIGHT_PINKY, lm.RIGHT_INDEX, lm.RIGHT_THUMB))):
        for e in extra:
            f[e] = f[w] + (0.0, -0.05, 0.0)
    f[lm.LEFT_HIP] = (-0.15, 1.0, 0.0)
    f[lm.RIGHT_HIP] = (0.15, 1.0, 0.0)
    f[lm.LEFT_KNEE] = (-0.15, 0.5, 0.0)
    f[lm.RIGHT_KNEE] = (0.15, 0.5, 0.0)
    f[lm.LEFT_ANKLE] = (-0.15, 0.0, 0.0)
    f[lm.RIGHT_ANKLE] = (0.15, 0.0, 0.0)
    f[lm.LEFT_HEEL] = (-0.15, -0.02, 0.0)
    f[lm.RIGHT_HEEL] = (0.15, -0.02, 0.0)
    f[lm.LEFT_FOOT_INDEX] = (-0.15, -0.02, 0.1)
    f[lm.RIGHT_FOOT_INDEX] = (0.15, -0.02, 0.1)
    return f


def set_knee_angle(frame: np.ndarray, angle_deg: float) -> None:
    """Place les chevilles pour obtenir un angle de genou donné (deux jambes)."""
    phi = np.radians(180.0 - angle_deg)
    offset = 0.5 * np.array([np.sin(phi), -np.cos(phi), 0.0])
    frame[lm.LEFT_ANKLE] = frame[lm.LEFT_KNEE] + offset
    frame[lm.RIGHT_ANKLE] = frame[lm.RIGHT_KNEE] + offset


def make_sequence(
    world: np.ndarray,
    image: np.ndarray | None = None,
    visibility: np.ndarray | None = None,
    fps: float = 30.0,
) -> PoseSequence:
    n = world.shape[0]
    if image is None:
        # Projection simple cohérente avec la convention image (y vers le bas).
        image = np.stack(
            [0.5 + 0.15 * world[:, :, 0], 0.55 - 0.15 * world[:, :, 1]], axis=-1
        )
    if visibility is None:
        visibility = np.ones((n, lm.NUM_LANDMARKS))
    return PoseSequence(
        world=world.astype(float),
        image=image.astype(float),
        visibility=visibility.astype(float),
        present=np.ones(n, dtype=bool),
        timestamps=np.arange(n) / fps,
        fps=fps,
        frame_width=640,
        frame_height=480,
        video_path="synthetic.mp4",
    )


@pytest.fixture
def shot_sequence() -> tuple[PoseSequence, dict[str, int]]:
    """Séquence synthétique d'un tir complet (4 s à 30 fps) + vérité terrain.

    Chronologie : stable jusqu'à 1.0 s, crouch (flexion max) à 1.5 s,
    release (poignet au plus haut, coude tendu) à 2.0 s, apex du saut à
    2.2 s, atterrissage vers 2.55 s.
    """
    fps = 30.0
    t = np.arange(0, 121) / fps

    knee = keyframes(t, [(0, 175), (1.0, 175), (1.5, 115), (2.0, 175), (4.0, 175)])
    elbow_pos_y = keyframes(t, [(0, 1.3), (1.5, 1.3), (2.0, 1.75), (2.6, 1.4), (4.0, 1.4)])
    elbow_pos_x = keyframes(t, [(0, 0.35), (1.5, 0.35), (2.0, 0.25), (2.6, 0.3), (4.0, 0.3)])
    wrist_pos_y = keyframes(t, [(0, 1.1), (1.5, 1.1), (2.0, 2.1), (2.6, 1.2), (4.0, 1.2)])
    # x du poignet à la release != x de l'épaule (0.2) : un axe épaule->poignet
    # parfaitement vertical rendrait le plan de tir (chicken wing) indéfini.
    wrist_pos_x = keyframes(t, [(0, 0.45), (1.5, 0.45), (2.0, 0.3), (2.6, 0.45), (4.0, 0.45)])
    # Mouvement vertical global du corps (descente puis saut), visible
    # uniquement en coordonnées image — comme avec MediaPipe (monde centré hanches).
    body_offset = keyframes(
        t, [(0, 0), (1.0, 0), (1.5, -0.15), (2.0, 0.1), (2.2, 0.3), (2.6, 0), (4.0, 0)]
    )

    world = np.zeros((len(t), lm.NUM_LANDMARKS, 3))
    for i in range(len(t)):
        f = standing_frame()
        set_knee_angle(f, knee[i])
        f[lm.RIGHT_ELBOW] = (elbow_pos_x[i], elbow_pos_y[i], 0.0)
        f[lm.RIGHT_WRIST] = (wrist_pos_x[i], wrist_pos_y[i], 0.0)
        world[i] = f

    image = np.stack(
        [
            0.5 + 0.15 * world[:, :, 0],
            0.55 - 0.15 * (world[:, :, 1] + body_offset[:, None]),
        ],
        axis=-1,
    )
    seq = make_sequence(world, image=image, fps=fps)
    truth = {"stance": 30, "crouch": 45, "release": 60, "jump_peak": 66, "landing": 76}
    return seq, truth
