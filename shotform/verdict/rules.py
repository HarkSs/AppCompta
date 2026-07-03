"""Moteur de règles : mesures vs référentiel -> statuts, score /100, conseils.

Entièrement déterministe : aucun LLM, uniquement des comparaisons aux plages
[p10, p90] du référentiel et des textes pré-rédigés (messages.py).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..pipeline.angles import METRIC_ORDER, Metric
from . import messages

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "reference"
REFERENCE_PATH = REFERENCE_DIR / "reference.json"
FALLBACK_PATH = REFERENCE_DIR / "reference_fallback.json"

# Pondération du score global. Justification :
# - elbow_angle (3.0) et elbow_lateral_offset (2.5) : la mécanique du coude à
#   la release est le déterminant n°1 de la régularité du tir — c'est ce que
#   corrigent en priorité tous les coachs de shooting.
# - release_height et forearm_elevation (2.0) : la hauteur et l'angle de sortie
#   conditionnent directement l'arc du ballon et la difficulté à contrer.
# - knee_flexion_shooting et body_alignment (1.5) : la base de la puissance et
#   du transfert d'énergie, mais plus variable selon les morphologies pros.
# - trunk_lean et crouch_to_release_time (1.0) : importants mais très
#   dépendants du style (catch-and-shoot vs off-the-dribble).
# - knee_flexion_opposite (0.75) et jump_symmetry (0.5) : indicateurs
#   d'équilibre secondaires, faible variance chez les pros comme les amateurs.
WEIGHTS: dict[str, float] = {
    "elbow_angle": 3.0,
    "elbow_lateral_offset": 2.5,
    "release_height": 2.0,
    "forearm_elevation": 2.0,
    "knee_flexion_shooting": 1.5,
    "body_alignment": 1.5,
    "trunk_lean": 1.0,
    "crouch_to_release_time": 1.0,
    "knee_flexion_opposite": 0.75,
    "jump_symmetry": 0.5,
}

# Marge « limite » : au-delà de la plage [p10, p90] mais à moins de
# BORDERLINE_FACTOR × (p90 - p10) de la borne, le statut est "limite".
BORDERLINE_FACTOR = 0.35


@dataclass
class MetricVerdict:
    metric: str
    label: str
    value: float
    unit: str
    status: str  # "bon" | "limite" | "a_corriger" | "incertain" | "sans_reference"
    score: float | None  # /100, None si hors score
    reference: dict | None
    deviation: float | None  # écart chiffré à la borne la plus proche (même unité)
    message: str


@dataclass
class Verdict:
    score: float | None  # /100
    reference_type: str  # "pro" | "fallback"
    items: list[MetricVerdict]
    excluded: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)


def load_reference(path: str | Path | None = None) -> dict:
    """Charge le référentiel pro s'il existe, sinon le fallback (marqué tel quel)."""
    if path is not None:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    if REFERENCE_PATH.is_file():
        return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    return json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))


def metric_score(value: float, lo: float, hi: float) -> tuple[str, float, float, str]:
    """Renvoie (status, score/100, écart à la borne, direction "low"/"high"/"in").

    - dans [p10, p90]                      -> "bon", 100
    - à moins de 35 % de la largeur de     -> "limite", 99..60 (linéaire)
      plage au-delà d'une borne
    - au-delà                              -> "a_corriger", 59..0 (linéaire,
      plancher 0 à 3× la marge limite)
    """
    span = max(hi - lo, 1e-9)
    tol = BORDERLINE_FACTOR * span
    if lo <= value <= hi:
        return "bon", 100.0, 0.0, "in"
    if value < lo:
        deviation, direction = lo - value, "low"
    else:
        deviation, direction = value - hi, "high"
    if deviation <= tol:
        score = 99.0 - 39.0 * (deviation / tol)
        return "limite", round(score, 1), deviation, direction
    extra = min((deviation - tol) / (2.0 * tol), 1.0)
    score = 59.0 * (1.0 - extra)
    return "a_corriger", round(score, 1), deviation, direction


def evaluate(
    metrics: dict[str, Metric],
    quality_per_metric: dict,
    reference: dict | None = None,
) -> Verdict:
    """Compare chaque métrique fiable au référentiel et calcule le score global."""
    ref = reference if reference is not None else load_reference()
    ref_type = ref.get("type", "pro")
    ref_metrics = ref.get("metrics", {})

    items: list[MetricVerdict] = []
    excluded: list[str] = []
    weighted_sum = 0.0
    weight_total = 0.0

    for name in METRIC_ORDER:
        if name not in metrics:
            continue
        m = metrics[name]
        conf = quality_per_metric.get(name)
        reliable = bool(conf.reliable) if conf is not None else True

        if not reliable:
            reasons = ", ".join(conf.reasons) if conf and conf.reasons else "confiance basse"
            items.append(MetricVerdict(
                metric=name, label=m.label, value=m.value, unit=m.unit,
                status="incertain", score=None, reference=ref_metrics.get(name),
                deviation=None,
                message=messages.UNRELIABLE_MESSAGE.format(label=m.label, reasons=reasons),
            ))
            excluded.append(name)
            continue

        ref_m = ref_metrics.get(name)
        if not ref_m or not ref_m.get("reliable", True):
            items.append(MetricVerdict(
                metric=name, label=m.label, value=m.value, unit=m.unit,
                status="sans_reference", score=None, reference=ref_m,
                deviation=None,
                message=messages.NO_REFERENCE_MESSAGE.format(label=m.label),
            ))
            excluded.append(name)
            continue

        lo, hi = float(ref_m["p10"]), float(ref_m["p90"])
        status, score, deviation, direction = metric_score(m.value, lo, hi)
        val_s = messages.format_value(m.value, m.unit)
        lo_s = messages.format_value(lo, m.unit)
        hi_s = messages.format_value(hi, m.unit)
        if status == "bon":
            msg = messages.GOOD_MESSAGE.format(label=m.label, value=val_s, lo=lo_s, hi=hi_s)
        elif status == "limite":
            msg = messages.BORDERLINE_MESSAGE.format(label=m.label, value=val_s, lo=lo_s, hi=hi_s)
        else:
            msg = messages.advice_for(name, direction, val_s, lo_s, hi_s)

        items.append(MetricVerdict(
            metric=name, label=m.label, value=round(m.value, 2), unit=m.unit,
            status=status, score=score,
            reference={"p10": lo, "p90": hi, "median": ref_m.get("median"), "n": ref_m.get("n")},
            deviation=round(deviation, 2), message=msg,
        ))
        w = WEIGHTS.get(name, 1.0)
        weighted_sum += w * score
        weight_total += w

    verdict = Verdict(
        score=round(weighted_sum / weight_total, 1) if weight_total > 0 else None,
        reference_type=ref_type,
        items=items,
        excluded=excluded,
    )
    if ref_type == "fallback":
        verdict.notices.append(messages.FALLBACK_NOTICE)
    if verdict.score is None:
        verdict.notices.append(
            "Aucune métrique fiable comparable : score global impossible. "
            "Refilmez avec un meilleur angle de prise de vue."
        )
    return verdict


def summary_text(verdict: Verdict, quality=None, phases_times: dict | None = None) -> str:
    """Résumé texte lisible (français) du verdict."""
    lines: list[str] = ["=== ShotForm — analyse du tir ===", ""]
    if verdict.score is not None:
        lines.append(f"Score global : {verdict.score:.0f} / 100")
    else:
        lines.append("Score global : non calculable")
    ref_label = "référentiel pro" if verdict.reference_type == "pro" else "référentiel de repli"
    lines.append(f"Référentiel utilisé : {ref_label}")
    if phases_times:
        lines.append("")
        lines.append("Phases détectées : " + ", ".join(
            f"{name} à {t:.2f} s" for name, t in phases_times.items()
        ))
    if quality is not None:
        lines.append(
            f"Orientation caméra : {quality.orientation} "
            f"(angle {quality.view_angle_deg}°), détection {quality.detection_rate:.0%}"
        )
    lines.append("")
    order = {"a_corriger": 0, "limite": 1, "bon": 2, "incertain": 3, "sans_reference": 4}
    for item in sorted(verdict.items, key=lambda i: order.get(i.status, 9)):
        badge = messages.STATUS_LABELS.get(item.status, item.status)
        lines.append(f"[{badge}] {item.message}")
    if quality is not None and quality.recommendation:
        lines.append("")
        lines.append("Conseil de prise de vue : " + quality.recommendation)
    for notice in verdict.notices:
        lines.append("")
        lines.append(notice)
    return "\n".join(lines) + "\n"
