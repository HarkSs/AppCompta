"""Découpe une vidéo continue (plan-séquence) en un clip par tir.

Contrairement à split_clips (changements de plan), ce script segmente par le
mouvement : la pose est extraite sur toute la vidéo, chaque pic marqué de
hauteur de poignet correspond à un tir, et une fenêtre [-2 s, +1.5 s] autour
de chaque pic est écrite comme clip séparé — prêt pour `build-reference`.

    python -m shotform.scripts.split_shots seance.mp4 shots/ [--model full]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .. import landmarks as lm
from ..pipeline.extractor import extract
from ..pipeline.video_io import finalize_mp4

# Fenêtre écrite autour de chaque pic de poignet (secondes).
PRE_S = 2.0
POST_S = 1.5
# Deux pics plus proches que cela sont fusionnés (on garde le plus haut).
MIN_SEPARATION_S = 1.5
# Proéminence minimale d'un pic, en fraction de l'amplitude totale du signal.
MIN_PROMINENCE = 0.25


def detect_shot_peaks(seq, min_separation_s: float = MIN_SEPARATION_S) -> list[int]:
    """Frames des pics de poignet (un par tir), tous poignets confondus."""
    heights = seq.image_heights()
    wrist = np.fmax(heights[:, lm.LEFT_WRIST], heights[:, lm.RIGHT_WRIST])
    finite = np.isfinite(wrist)
    if not finite.any():
        return []
    span = float(np.nanmax(wrist) - np.nanmin(wrist))
    if span <= 1e-9:
        return []
    floor = float(np.nanmin(wrist))
    threshold = floor + (1.0 - MIN_PROMINENCE) * span

    # Maxima locaux au-dessus du seuil, puis fusion des pics trop proches.
    candidates = [
        i for i in range(1, len(wrist) - 1)
        if finite[i] and wrist[i] >= threshold
        and wrist[i] >= np.nan_to_num(wrist[i - 1], nan=-np.inf)
        and wrist[i] > np.nan_to_num(wrist[i + 1], nan=-np.inf)
    ]
    min_gap = int(round(min_separation_s * seq.fps))
    peaks: list[int] = []
    for c in candidates:
        if peaks and c - peaks[-1] < min_gap:
            if wrist[c] > wrist[peaks[-1]]:
                peaks[-1] = c
        else:
            peaks.append(c)
    return peaks


def split_by_shots(
    video_path: str | Path,
    out_dir: str | Path,
    *,
    model_variant: str = "full",
    pre_s: float = PRE_S,
    post_s: float = POST_S,
) -> list[Path]:
    """Écrit un clip par tir détecté. Le modèle `full` suffit pour segmenter
    (la construction du référentiel ré-extrait ensuite en `heavy`)."""
    import cv2

    video_path = Path(video_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    seq = extract(video_path, model_variant=model_variant)
    peaks = detect_shot_peaks(seq)
    if not peaks:
        print(f"{video_path.name} : aucun tir détecté.")
        return []

    windows = [
        (max(0, p - int(round(pre_s * seq.fps))),
         min(len(seq), p + int(round(post_s * seq.fps))))
        for p in peaks
    ]

    cap = cv2.VideoCapture(str(video_path))
    written: list[Path] = []
    prefix = video_path.stem[:24]
    for k, (a, b) in enumerate(windows):
        path = out_dir / f"{prefix}_shot{k:03d}.mp4"
        writer = cv2.VideoWriter(
            str(path), cv2.VideoWriter_fourcc(*"mp4v"), seq.fps,
            (seq.frame_width, seq.frame_height),
        )
        cap.set(cv2.CAP_PROP_POS_FRAMES, a)
        for _ in range(a, b):
            ok, frame = cap.read()
            if not ok:
                break
            writer.write(frame)
        writer.release()
        written.append(finalize_mp4(path))
    cap.release()

    print(f"{video_path.name} : {len(peaks)} tirs détectés -> {len(written)} clips dans {out_dir}")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("video", help="Vidéo continue contenant plusieurs tirs.")
    parser.add_argument("out_dir", help="Dossier de sortie des clips.")
    parser.add_argument("--model", choices=["heavy", "full"], default="full")
    args = parser.parse_args(argv)
    split_by_shots(args.video, args.out_dir, model_variant=args.model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
