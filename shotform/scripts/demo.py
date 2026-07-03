"""Démo de bout en bout : analyse une vidéo de test et affiche le rapport.

    python -m shotform.scripts.demo chemin/vers/tir.mp4 [right|left]

Équivalent à `python -m shotform analyze <video> --side <side> --out demo_report/`,
avec un affichage pas-à-pas de chaque étape du pipeline.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 1
    video = Path(argv[0])
    side = argv[1] if len(argv) > 1 else None

    from ..analyze import analyze_video
    from ..cli import main as cli_main

    print(f"=== Démo ShotForm — {video.name} ===")
    print("1/5 extraction des poses 3D (MediaPipe, heavy)…")
    analysis = analyze_video(video, shooting_side=side)
    seq = analysis.seq
    print(
        f"    {len(seq)} frames à {seq.fps:.0f} fps, "
        f"détection {seq.detection_rate():.0%}"
    )
    print(f"2/5 phases : " + ", ".join(
        f"{k}=f{v} ({seq.timestamps[v]:.2f}s)" for k, v in analysis.phases.as_dict().items()
    ))
    print(f"3/5 côté de tir : {analysis.shooting_side} ({analysis.side_source})")
    print(
        f"4/5 qualité : orientation {analysis.quality.orientation}, "
        f"angle de vue {analysis.quality.view_angle_deg}°"
    )
    print("5/5 verdict + rapport complet via la CLI :")
    print()
    args = ["analyze", str(video), "--out", "demo_report"]
    if side:
        args += ["--side", side]
    return cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
