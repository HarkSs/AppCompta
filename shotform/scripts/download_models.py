"""Télécharge les modèles PoseLandmarker (une seule fois, à l'installation).

Après ce téléchargement, ShotForm fonctionne 100 % hors ligne : aucun appel
réseau au runtime.

    python -m shotform.scripts.download_models          # heavy + full
    python -m shotform.scripts.download_models heavy    # un seul modèle
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

from ..pipeline.extractor import DEFAULT_MODELS_DIR, MODEL_FILENAMES

_BASE = "https://storage.googleapis.com/mediapipe-models/pose_landmarker"
URLS = {
    "heavy": f"{_BASE}/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
    "full": f"{_BASE}/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
}


def download(variant: str) -> Path:
    dest = DEFAULT_MODELS_DIR / MODEL_FILENAMES[variant]
    if dest.is_file():
        print(f"{dest} déjà présent, rien à faire.")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement du modèle {variant} ...")
    urllib.request.urlretrieve(URLS[variant], dest)
    print(f"OK : {dest}")
    return dest


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    variants = argv or list(URLS)
    for variant in variants:
        if variant not in URLS:
            print(f"Variante inconnue : {variant} (attendu : {', '.join(URLS)})")
            return 1
        download(variant)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
