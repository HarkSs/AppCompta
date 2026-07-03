"""Vidéo annotée de debug/vérification : squelette, phases, angles clés.

Utilisée par `analyze` (annotated.mp4) et par `build-reference --review`
pour valider visuellement les détections sur chaque clip pro.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .. import landmarks as lm
from .angles import angle_deg_series
from .extractor import PoseSequence
from .phases import Phases
from .video_io import finalize_mp4

# Couleurs BGR
_SKELETON = (0, 200, 255)
_JOINT = (255, 255, 255)
_TEXT = (255, 255, 255)
_PHASE_FLASH = (0, 80, 255)

_PHASE_LABELS = {
    "stance": "STANCE",
    "crouch": "CROUCH",
    "release": "RELEASE",
    "landing": "LANDING",
}


def _segment_label(i: int, phases: Phases) -> str:
    if i < phases.stance:
        return "préparation"
    if i < phases.crouch:
        return "flexion"
    if i < phases.release:
        return "montée"
    if i <= phases.landing:
        return "vol"
    return "réception"


def annotate_video(
    seq: PoseSequence,
    phases: Phases,
    shooting_side: str,
    out_path: str | Path,
    score: float | None = None,
) -> Path:
    """Réécrit la vidéo source avec squelette, phases et angles incrustés."""
    import cv2  # import paresseux

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    side = lm.side_landmarks(shooting_side)
    w = seq.world
    elbow = angle_deg_series(w[:, side["shoulder"]], w[:, side["elbow"]], w[:, side["wrist"]])
    knee = angle_deg_series(w[:, side["hip"]], w[:, side["knee"]], w[:, side["ankle"]])

    cap = cv2.VideoCapture(seq.video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Impossible de relire la vidéo : {seq.video_path}")
    writer = cv2.VideoWriter(
        str(out_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        seq.fps,
        (seq.frame_width, seq.frame_height),
    )
    phase_frames = {v: k for k, v in phases.as_dict().items()}
    flash_len = max(2, int(round(0.1 * seq.fps)))

    i = 0
    while True:
        ok, frame = cap.read()
        if not ok or i >= len(seq):
            break
        if seq.present[i]:
            _draw_skeleton(cv2, frame, seq.image[i], seq.frame_width, seq.frame_height)
            _draw_joint_angle(cv2, frame, seq, i, side["elbow"], elbow[i], "coude")
            _draw_joint_angle(cv2, frame, seq, i, side["knee"], knee[i], "genou")

        header = f"{_segment_label(i, phases)}  t={seq.timestamps[i]:.2f}s"
        if score is not None:
            header += f"  score={score:.0f}/100"
        cv2.putText(frame, header, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, _TEXT, 2)

        for phase_idx, name in phase_frames.items():
            if phase_idx <= i < phase_idx + flash_len:
                cv2.putText(
                    frame, _PHASE_LABELS[name],
                    (10, seq.frame_height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, _PHASE_FLASH, 3,
                )
        writer.write(frame)
        i += 1

    cap.release()
    writer.release()
    return finalize_mp4(out_path)


def _draw_skeleton(cv2, frame, image_lms: np.ndarray, width: int, height: int) -> None:
    pts = image_lms * np.array([width, height])
    for a, b in lm.POSE_CONNECTIONS:
        pa, pb = pts[a], pts[b]
        if np.isfinite(pa).all() and np.isfinite(pb).all():
            cv2.line(frame, tuple(pa.astype(int)), tuple(pb.astype(int)), _SKELETON, 2)
    for p in pts:
        if np.isfinite(p).all():
            cv2.circle(frame, tuple(p.astype(int)), 3, _JOINT, -1)


def _draw_joint_angle(cv2, frame, seq: PoseSequence, i: int, joint: int, value: float, label: str) -> None:
    if not np.isfinite(value):
        return
    p = seq.image[i, joint] * np.array([seq.frame_width, seq.frame_height])
    if not np.isfinite(p).all():
        return
    x, y = int(p[0]) + 8, int(p[1]) - 8
    cv2.putText(frame, f"{label} {value:.0f}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, _TEXT, 2)
