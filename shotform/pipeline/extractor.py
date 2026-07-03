"""Extraction : vidéo -> séquence de squelettes 3D par frame.

Utilise MediaPipe Tasks PoseLandmarker (modèle "heavy" par défaut, "full" en
fallback perf) en mode VIDEO, sans masque de segmentation, et récupère les
`pose_world_landmarks` (coordonnées 3D en mètres, origine au centre des
hanches) — quasi invariants au point de vue de la caméra.

Convention interne : l'axe Y des coordonnées monde ET des hauteurs image est
retourné pour pointer VERS LE HAUT (MediaPipe utilise y vers le bas). Les
coordonnées image normalisées brutes (y vers le bas) sont conservées à part
pour le dessin.

Les imports MediaPipe/OpenCV sont paresseux : la géométrie, les phases et le
verdict restent testables sans ces dépendances.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..landmarks import NUM_LANDMARKS
from .smoothing import interpolate_gaps, savgol_filter

# Durée maximale d'un trou de détection interpolable / tolérée (secondes).
MAX_GAP_S = 0.5

MODEL_FILENAMES = {
    "heavy": "pose_landmarker_heavy.task",
    "full": "pose_landmarker_full.task",
}
DEFAULT_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


@dataclass
class PoseSequence:
    """Séquence de poses extraites d'une vidéo.

    world : (T, 33, 3) mètres, origine hanches, Y vers le haut ; NaN si absent.
    image : (T, 33, 2) coordonnées normalisées brutes (x droite, y bas).
    visibility : (T, 33) visibilité MediaPipe dans [0, 1].
    present : (T,) True si une pose a été détectée sur la frame.
    """

    world: np.ndarray
    image: np.ndarray
    visibility: np.ndarray
    present: np.ndarray
    timestamps: np.ndarray  # (T,) secondes
    fps: float
    frame_width: int
    frame_height: int
    video_path: str = ""
    warnings: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.timestamps)

    def image_heights(self) -> np.ndarray:
        """Hauteurs image (T, 33) : plus grand = plus haut à l'écran."""
        return -self.image[:, :, 1]

    def detection_rate(self) -> float:
        return float(self.present.mean()) if len(self) else 0.0


def resolve_model_path(model_variant: str = "heavy", model_path: str | None = None) -> Path:
    """Trouve le fichier .task : argument > $SHOTFORM_MODEL_PATH > shotform/models/."""
    if model_path:
        p = Path(model_path)
        if p.is_file():
            return p
        raise FileNotFoundError(f"Modèle introuvable : {p}")
    env = os.environ.get("SHOTFORM_MODEL_PATH")
    if env and Path(env).is_file():
        return Path(env)
    if model_variant not in MODEL_FILENAMES:
        raise ValueError(f"Variante de modèle inconnue : {model_variant!r}")
    candidate = DEFAULT_MODELS_DIR / MODEL_FILENAMES[model_variant]
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(
        f"Modèle PoseLandmarker absent ({candidate}).\n"
        "Téléchargez-le une seule fois (ensuite tout fonctionne hors ligne) :\n"
        "  python -m shotform.scripts.download_models"
    )


def extract(
    video_path: str | Path,
    *,
    model_variant: str = "heavy",
    model_path: str | None = None,
    smooth: bool = True,
) -> PoseSequence:
    """Extrait les world landmarks 3D de chaque frame d'une vidéo.

    numPoses=2 uniquement pour DÉTECTER la présence d'une deuxième personne
    (signalée dans le rapport) ; seule la pose principale est analysée.
    """
    video_path = Path(video_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"Vidéo introuvable : {video_path}")
    task_path = resolve_model_path(model_variant, model_path)

    import cv2  # import paresseux
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    options = mp_vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(task_path)),
        running_mode=mp_vision.RunningMode.VIDEO,
        num_poses=2,
        output_segmentation_masks=False,
    )

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la vidéo : {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    world_list: list[np.ndarray] = []
    image_list: list[np.ndarray] = []
    vis_list: list[np.ndarray] = []
    present_list: list[bool] = []
    multi_person_frames = 0

    nan_world = np.full((NUM_LANDMARKS, 3), np.nan)
    nan_image = np.full((NUM_LANDMARKS, 2), np.nan)
    zero_vis = np.zeros(NUM_LANDMARKS)

    with mp_vision.PoseLandmarker.create_from_options(options) as landmarker:
        frame_idx = 0
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break
            ts_ms = int(round(frame_idx * 1000.0 / fps))
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB),
            )
            result = landmarker.detect_for_video(mp_image, ts_ms)
            if result.pose_world_landmarks:
                if len(result.pose_world_landmarks) > 1:
                    multi_person_frames += 1
                world_lms = result.pose_world_landmarks[0]
                img_lms = result.pose_landmarks[0]
                world = np.array([[lm.x, -lm.y, lm.z] for lm in world_lms])
                image = np.array([[lm.x, lm.y] for lm in img_lms])
                vis = np.array([lm.visibility for lm in world_lms])
                world_list.append(world)
                image_list.append(image)
                vis_list.append(vis)
                present_list.append(True)
            else:
                world_list.append(nan_world.copy())
                image_list.append(nan_image.copy())
                vis_list.append(zero_vis.copy())
                present_list.append(False)
            frame_idx += 1
    cap.release()

    if frame_idx == 0:
        raise RuntimeError(f"Aucune frame lisible dans {video_path}")

    seq = PoseSequence(
        world=np.stack(world_list),
        image=np.stack(image_list),
        visibility=np.stack(vis_list),
        present=np.array(present_list),
        timestamps=np.arange(frame_idx) / fps,
        fps=float(fps),
        frame_width=width,
        frame_height=height,
        video_path=str(video_path),
    )

    if multi_person_frames > 0.1 * frame_idx:
        seq.warnings.append(
            "Plusieurs personnes détectées à l'image : seule la personne "
            "principale a été analysée. Vérifiez le cadrage."
        )
    _flag_gaps(seq)
    if smooth:
        smooth_sequence(seq)
    return seq


def _flag_gaps(seq: PoseSequence) -> None:
    """Signale les pertes de détection > MAX_GAP_S et le taux de détection global."""
    if not seq.present.any():
        seq.warnings.append("Aucune pose détectée dans la vidéo.")
        return
    max_gap_frames = int(round(MAX_GAP_S * seq.fps))
    run = 0
    worst = 0
    for p in seq.present:
        run = 0 if p else run + 1
        worst = max(worst, run)
    if worst > max_gap_frames:
        seq.warnings.append(
            f"Détection perdue pendant {worst / seq.fps:.1f} s : les mesures "
            "autour de ce trou sont incertaines."
        )


def smooth_sequence(seq: PoseSequence, window_s: float = 0.15) -> None:
    """Interpole les petits trous puis lisse les trajectoires (in place)."""
    max_gap_frames = max(1, int(round(MAX_GAP_S * seq.fps)))
    seq.world = interpolate_gaps(seq.world, seq.present, max_gap_frames)
    seq.image = interpolate_gaps(seq.image, seq.present, max_gap_frames)
    window = max(5, int(round(window_s * seq.fps)) | 1)
    seq.world = savgol_filter(seq.world, window)
    seq.image = savgol_filter(seq.image, window)
