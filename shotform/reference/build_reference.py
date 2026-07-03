"""Construction du référentiel : dossier de clips pros -> reference.json.

Pour chaque clip, le pipeline complet tourne (extraction, phases, angles,
qualité) ; seules les mesures FIABLES (confiance suffisante) alimentent le
référentiel. Le mode --review génère une vidéo annotée par clip (squelette +
phases + angles) pour valider visuellement les détections avant d'adopter le
référentiel — un référentiel construit sur des détections fausses ruine tout.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..pipeline.angles import METRIC_ORDER

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}
MIN_SAMPLES = 5  # en dessous, la plage est marquée non fiable


def aggregate_samples(samples: dict[str, list[float]], units: dict[str, str]) -> dict:
    """Agrège les mesures par métrique : médiane, [p10, p90], n, fiabilité."""
    metrics = {}
    for name in METRIC_ORDER:
        values = [v for v in samples.get(name, []) if np.isfinite(v)]
        if not values:
            metrics[name] = {
                "median": None, "p10": None, "p90": None,
                "n": 0, "reliable": False, "unit": units.get(name, ""),
            }
            continue
        arr = np.array(values, dtype=float)
        metrics[name] = {
            "median": round(float(np.median(arr)), 3),
            "p10": round(float(np.percentile(arr, 10)), 3),
            "p90": round(float(np.percentile(arr, 90)), 3),
            "n": len(values),
            "reliable": len(values) >= MIN_SAMPLES,
            "unit": units.get(name, ""),
        }
    return metrics


def build_reference(
    clips_dir: str | Path,
    *,
    out_path: str | Path | None = None,
    review: bool = False,
    model_variant: str = "heavy",
    model_path: str | None = None,
    exclude: set[str] | None = None,
) -> dict:
    """Analyse tous les clips du dossier et écrit reference.json.

    `exclude` : métriques à ne PAS mettre dans le référentiel (ex. les
    métriques de timing quand les clips sources sont des ralentis).
    """
    exclude = set(exclude or ())
    from ..analyze import analyze_video  # import ici pour rester léger en test

    clips_dir = Path(clips_dir)
    if not clips_dir.is_dir():
        raise FileNotFoundError(f"Dossier de clips introuvable : {clips_dir}")
    clips = sorted(
        p for p in clips_dir.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not clips:
        raise FileNotFoundError(f"Aucune vidéo ({', '.join(sorted(VIDEO_EXTENSIONS))}) dans {clips_dir}")

    if out_path is None:
        out_path = Path(__file__).resolve().parent / "reference.json"
    out_path = Path(out_path)
    review_dir = clips_dir / "review"

    samples: dict[str, list[float]] = {name: [] for name in METRIC_ORDER}
    units: dict[str, str] = {}
    clip_reports: list[dict] = []

    for clip in clips:
        print(f"[build-reference] {clip.name} ...")
        try:
            analysis = analyze_video(
                clip, model_variant=model_variant, model_path=model_path
            )
        except Exception as exc:  # un clip cassé ne doit pas bloquer le lot
            print(f"  ÉCHEC : {exc}")
            clip_reports.append({"clip": clip.name, "status": "erreur", "error": str(exc)})
            continue

        used, skipped = [], []
        for name, metric in analysis.metrics.items():
            units[name] = metric.unit
            if name in exclude:
                continue
            conf = analysis.quality.per_metric[name]
            if conf.reliable and np.isfinite(metric.value):
                samples[name].append(float(metric.value))
                used.append(name)
            else:
                skipped.append(name)
        clip_reports.append({
            "clip": clip.name,
            "status": "ok",
            "shooting_side": analysis.shooting_side,
            "orientation": analysis.quality.orientation,
            "metrics_used": used,
            "metrics_skipped": skipped,
            "warnings": analysis.warnings,
        })
        if skipped:
            print(f"  métriques écartées (confiance basse) : {', '.join(skipped)}")

        if review:
            from ..pipeline.annotate import annotate_video

            review_path = review_dir / f"{clip.stem}_annotated.mp4"
            annotate_video(
                analysis.seq, analysis.phases, analysis.shooting_side, review_path
            )
            print(f"  vidéo de vérification : {review_path}")

    reference = {
        "type": "pro",
        "description": "Référentiel construit à partir de clips de shooters d'élite.",
        "excluded_metrics": sorted(exclude),
        "clips": clip_reports,
        "metrics": aggregate_samples(samples, units),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[build-reference] écrit : {out_path}")

    weak = [n for n, m in reference["metrics"].items() if not m["reliable"]]
    if weak:
        print(
            "ATTENTION — métriques avec moins de "
            f"{MIN_SAMPLES} échantillons exploitables (marquées non fiables) : "
            + ", ".join(weak)
        )
    if review:
        print(
            f"Vérifiez visuellement chaque vidéo de {review_dir} avant "
            "d'utiliser ce référentiel."
        )
    return reference
