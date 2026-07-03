"""Découpe une compilation vidéo en clips individuels par changement de plan.

Les vidéos de tirs pros trouvées en ligne sont souvent des compilations
(plusieurs tirs, angles multiples, ralentis) alors que le pipeline attend un
clip de 2-10 s contenant UN tir. Ce script détecte les changements de plan
(distance de Bhattacharyya entre histogrammes HSV de frames consécutives) et
écrit chaque segment assez long dans un dossier, prêt pour `build-reference`.

    python -m shotform.scripts.split_clips compilation.mp4 pro_clips/
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

# Seuil de distance d'histogramme au-delà duquel on considère un changement de plan.
CUT_THRESHOLD = 0.5
# Durées de segment conservées (les ralentis peuvent étirer un tir jusqu'à ~30 s).
MIN_LEN_S = 2.0
MAX_LEN_S = 40.0


def _frame_hist(cv2, frame) -> np.ndarray:
    small = cv2.resize(frame, (160, 90))
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist


def detect_cuts(video_path: str | Path, threshold: float = CUT_THRESHOLD) -> tuple[list[int], int, float]:
    """Renvoie (index des frames de coupe, nombre total de frames, fps)."""
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir : {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cuts: list[int] = []
    prev = None
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        hist = _frame_hist(cv2, frame)
        if prev is not None:
            dist = cv2.compareHist(prev, hist, cv2.HISTCMP_BHATTACHARYYA)
            if dist > threshold:
                cuts.append(i)
        prev = hist
        i += 1
    cap.release()
    return cuts, i, fps


def split(
    video_path: str | Path,
    out_dir: str | Path,
    *,
    threshold: float = CUT_THRESHOLD,
    min_len_s: float = MIN_LEN_S,
    max_len_s: float = MAX_LEN_S,
    prefix: str | None = None,
) -> list[Path]:
    """Écrit chaque segment [coupe, coupe suivante) comme un clip séparé."""
    import cv2

    video_path = Path(video_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = prefix or video_path.stem[:24]

    cuts, total, fps = detect_cuts(video_path, threshold)
    bounds = [0, *cuts, total]
    segments = [
        (a, b) for a, b in zip(bounds, bounds[1:])
        if min_len_s <= (b - a) / fps <= max_len_s
    ]

    cap = cv2.VideoCapture(str(video_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    written: list[Path] = []
    seg_iter = iter(segments)
    current = next(seg_iter, None)
    writer = None
    i = 0
    while current is not None:
        ok, frame = cap.read()
        if not ok:
            break
        a, b = current
        if i == a:
            path = out_dir / f"{prefix}_{len(written):03d}.mp4"
            writer = cv2.VideoWriter(
                str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
            )
            written.append(path)
        if writer is not None and a <= i < b:
            writer.write(frame)
        if i == b - 1 and writer is not None:
            writer.release()
            writer = None
            current = next(seg_iter, None)
        i += 1
    if writer is not None:
        writer.release()
    cap.release()

    print(f"{video_path.name} : {len(cuts)} coupes, {len(written)} clips gardés "
          f"({min_len_s:.0f}-{max_len_s:.0f} s) -> {out_dir}")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("video", help="Compilation vidéo à découper.")
    parser.add_argument("out_dir", help="Dossier de sortie des clips.")
    parser.add_argument("--threshold", type=float, default=CUT_THRESHOLD)
    parser.add_argument("--min-len", type=float, default=MIN_LEN_S)
    parser.add_argument("--max-len", type=float, default=MAX_LEN_S)
    args = parser.parse_args(argv)
    split(
        args.video, args.out_dir,
        threshold=args.threshold, min_len_s=args.min_len, max_len_s=args.max_len,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
