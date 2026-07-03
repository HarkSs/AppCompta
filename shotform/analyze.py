"""Orchestration de bout en bout : vidéo -> rapport structuré.

Séparé de cli.py pour être réutilisable (build_reference, tests, future UI).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .pipeline.angles import Metric, compute_metrics
from .pipeline.extractor import PoseSequence, extract
from .pipeline.phases import Phases, detect_phases, detect_shooting_side
from .pipeline.quality import QualityReport, assess_quality
from .verdict.rules import Verdict, evaluate, load_reference


@dataclass
class Analysis:
    seq: PoseSequence
    shooting_side: str
    side_source: str  # "user" | "auto"
    phases: Phases
    metrics: dict[str, Metric]
    quality: QualityReport
    verdict: Verdict
    warnings: list[str]

    def report(self) -> dict:
        """Rapport JSON-sérialisable."""
        return {
            "shotform_version": __version__,
            "video": self.seq.video_path,
            "shooting_side": self.shooting_side,
            "side_source": self.side_source,
            "phases": {
                name: {
                    "frame": idx,
                    "time_s": round(float(self.seq.timestamps[idx]), 3),
                }
                for name, idx in self.phases.as_dict().items()
            },
            "metrics": {
                name: {
                    "label": m.label,
                    "value": round(m.value, 3) if m.value == m.value else None,
                    "unit": m.unit,
                    "phase": m.phase,
                    "confidence": self.quality.per_metric[name].confidence,
                    "reliable": self.quality.per_metric[name].reliable,
                    "confidence_reasons": self.quality.per_metric[name].reasons,
                }
                for name, m in self.metrics.items()
            },
            "quality": {
                "view_angle_deg": self.quality.view_angle_deg,
                "orientation": self.quality.orientation,
                "facing_camera": self.quality.facing_camera,
                "detection_rate": self.quality.detection_rate,
                "recommendation": self.quality.recommendation,
            },
            "verdict": {
                "score": self.verdict.score,
                "reference_type": self.verdict.reference_type,
                "excluded_metrics": self.verdict.excluded,
                "notices": self.verdict.notices,
                "items": [
                    {
                        "metric": it.metric,
                        "label": it.label,
                        "value": it.value if it.value == it.value else None,
                        "unit": it.unit,
                        "status": it.status,
                        "score": it.score,
                        "reference": it.reference,
                        "deviation": it.deviation,
                        "message": it.message,
                    }
                    for it in self.verdict.items
                ],
            },
            "warnings": self.warnings,
        }


def analyze_video(
    video_path: str | Path,
    *,
    shooting_side: str | None = None,
    model_variant: str = "heavy",
    model_path: str | None = None,
    reference_path: str | Path | None = None,
) -> Analysis:
    """Pipeline complet sur une vidéo contenant UN tir."""
    seq = extract(video_path, model_variant=model_variant, model_path=model_path)
    return analyze_sequence(
        seq, shooting_side=shooting_side, reference_path=reference_path
    )


def analyze_sequence(
    seq: PoseSequence,
    *,
    shooting_side: str | None = None,
    reference_path: str | Path | None = None,
) -> Analysis:
    """Analyse une séquence déjà extraite (testable sans MediaPipe)."""
    warnings = list(seq.warnings)

    auto_side = detect_shooting_side(seq)
    if shooting_side is None:
        side, side_source = auto_side, "auto"
        warnings.append(
            f"Côté de tir non fourni : détection automatique -> {side}."
        )
    else:
        side, side_source = shooting_side, "user"
        if auto_side != shooting_side:
            warnings.append(
                f"Côté fourni ({shooting_side}) différent de la détection "
                f"automatique ({auto_side}) : vérifiez le paramètre --side."
            )

    phases = detect_phases(seq, side)
    warnings.extend(phases.warnings)
    metrics = compute_metrics(seq, phases, side)
    quality = assess_quality(seq, phases, metrics, side)
    warnings.extend(quality.warnings)
    reference = load_reference(reference_path)
    verdict = evaluate(metrics, quality.per_metric, reference)

    return Analysis(
        seq=seq,
        shooting_side=side,
        side_source=side_source,
        phases=phases,
        metrics=metrics,
        quality=quality,
        verdict=verdict,
        warnings=warnings,
    )
