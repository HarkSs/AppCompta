"""Point d'entrée CLI.

    python -m shotform analyze video.mp4 --side right --out report/
    python -m shotform build-reference pro_clips/ --review
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shotform",
        description="Analyse biomécanique locale de tirs au basket (100 % hors ligne).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_an = sub.add_parser("analyze", help="Analyse une vidéo contenant UN tir.")
    p_an.add_argument("video", help="Chemin de la vidéo (mp4/mov, 2-10 s).")
    p_an.add_argument(
        "--side", choices=["right", "left"], default=None,
        help="Côté du bras de tir (détection automatique si omis).",
    )
    p_an.add_argument("--out", default="report", help="Dossier de sortie (défaut : report/).")
    p_an.add_argument(
        "--model", choices=["heavy", "full"], default="heavy",
        help="Modèle PoseLandmarker : heavy (précision, défaut) ou full (plus rapide).",
    )
    p_an.add_argument("--model-path", default=None, help="Chemin explicite du fichier .task.")
    p_an.add_argument("--reference", default=None, help="Chemin d'un reference.json spécifique.")
    p_an.add_argument(
        "--no-video", action="store_true",
        help="Ne pas générer annotated.mp4 (plus rapide).",
    )

    p_ref = sub.add_parser(
        "build-reference", help="Construit reference.json depuis un dossier de clips pros."
    )
    p_ref.add_argument("clips_dir", help="Dossier contenant les clips de tirs pros.")
    p_ref.add_argument(
        "--review", action="store_true",
        help="Génère une vidéo annotée par clip pour vérification visuelle.",
    )
    p_ref.add_argument("--out", default=None, help="Chemin de sortie du reference.json.")
    p_ref.add_argument("--model", choices=["heavy", "full"], default="heavy")
    p_ref.add_argument("--model-path", default=None)
    return parser


def cmd_analyze(args: argparse.Namespace) -> int:
    from .analyze import analyze_video
    from .verdict.rules import summary_text

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    analysis = analyze_video(
        args.video,
        shooting_side=args.side,
        model_variant=args.model,
        model_path=args.model_path,
        reference_path=args.reference,
    )
    report = analysis.report()

    report_path = out_dir / "report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    phases_times = {
        name: info["time_s"] for name, info in report["phases"].items()
    }
    summary = summary_text(analysis.verdict, analysis.quality, phases_times)
    if analysis.warnings:
        summary += "\nAvertissements :\n" + "\n".join(
            f"- {w}" for w in analysis.warnings
        ) + "\n"
    summary_path = out_dir / "summary.txt"
    summary_path.write_text(summary, encoding="utf-8")

    print(summary)
    print(f"Rapport JSON : {report_path}")
    print(f"Résumé       : {summary_path}")

    if not args.no_video:
        from .pipeline.annotate import annotate_video

        video_path = annotate_video(
            analysis.seq,
            analysis.phases,
            analysis.shooting_side,
            out_dir / "annotated.mp4",
            score=analysis.verdict.score,
        )
        print(f"Vidéo annotée : {video_path}")
    return 0


def cmd_build_reference(args: argparse.Namespace) -> int:
    from .reference.build_reference import build_reference

    build_reference(
        args.clips_dir,
        out_path=args.out,
        review=args.review,
        model_variant=args.model,
        model_path=args.model_path,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "analyze":
            return cmd_analyze(args)
        if args.command == "build-reference":
            return cmd_build_reference(args)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    except ModuleNotFoundError as exc:
        print(
            f"Erreur : dépendance manquante ({exc.name}). "
            "Installez-les avec : pip install -r shotform/requirements.txt",
            file=sys.stderr,
        )
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
