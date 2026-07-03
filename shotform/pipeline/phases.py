"""Détection des 4 phases clés du tir : stance, crouch, release, landing.

La détection travaille sur des signaux 1-D dérivés de la séquence de poses
(hauteurs image pour les événements globaux, angles 3D pour l'état
articulaire) — ce qui la rend testable sur des trajectoires synthétiques via
`detect_phases_from_signals`.

Pourquoi les hauteurs IMAGE et pas les hauteurs monde ? Les world landmarks
MediaPipe sont centrés sur les hanches à chaque frame : le mouvement vertical
global (saut, descente) y est invisible. Les événements temporels sont donc
détectés en coordonnées image, et les angles articulaires sont calculés en 3D
monde (invariants au point de vue).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .. import landmarks as lm
from .angles import angle_deg_series
from .extractor import PoseSequence


@dataclass
class PhaseSignals:
    """Signaux 1-D (tous de même longueur) utilisés pour la détection."""

    t: np.ndarray            # secondes
    hip_height: np.ndarray   # hauteur image du centre des hanches (haut = grand)
    knee_angle: np.ndarray   # angle 3D moyen des deux genoux (deg)
    wrist_height: np.ndarray  # hauteur image du poignet de tir
    elbow_angle: np.ndarray  # angle 3D du coude de tir (deg)
    ankle_height: np.ndarray  # hauteur image moyenne des deux chevilles


@dataclass
class Phases:
    """Index de frame de chaque phase + apex du saut."""

    stance: int
    crouch: int
    release: int
    landing: int
    jump_peak: int
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, int]:
        return {
            "stance": self.stance,
            "crouch": self.crouch,
            "release": self.release,
            "landing": self.landing,
        }


def build_signals(seq: PoseSequence, shooting_side: str) -> PhaseSignals:
    """Dérive les signaux de détection depuis une séquence de poses."""
    side = lm.side_landmarks(shooting_side)
    heights = seq.image_heights()
    w = seq.world
    knee_l = angle_deg_series(w[:, lm.LEFT_HIP], w[:, lm.LEFT_KNEE], w[:, lm.LEFT_ANKLE])
    knee_r = angle_deg_series(w[:, lm.RIGHT_HIP], w[:, lm.RIGHT_KNEE], w[:, lm.RIGHT_ANKLE])
    return PhaseSignals(
        t=seq.timestamps,
        hip_height=(heights[:, lm.LEFT_HIP] + heights[:, lm.RIGHT_HIP]) / 2,
        knee_angle=np.nanmean(np.stack([knee_l, knee_r]), axis=0),
        wrist_height=heights[:, side["wrist"]],
        elbow_angle=angle_deg_series(
            w[:, side["shoulder"]], w[:, side["elbow"]], w[:, side["wrist"]]
        ),
        ankle_height=(heights[:, lm.LEFT_ANKLE] + heights[:, lm.RIGHT_ANKLE]) / 2,
    )


def detect_phases(seq: PoseSequence, shooting_side: str) -> Phases:
    return detect_phases_from_signals(build_signals(seq, shooting_side))


def detect_phases_from_signals(sig: PhaseSignals) -> Phases:
    """Détecte les 4 phases sur des signaux 1-D. Clip attendu : UN tir, 2-10 s."""
    n = len(sig.t)
    if n < 10:
        raise ValueError("Clip trop court pour détecter les phases (< 10 frames).")
    warnings: list[str] = []
    fps = 1.0 / float(np.median(np.diff(sig.t))) if n > 1 else 30.0

    release = _detect_release(sig, fps, warnings)
    crouch = _detect_crouch(sig, release, fps, warnings)
    stance = _detect_stance(sig, crouch, fps)
    jump_peak, landing = _detect_landing(sig, release, crouch, fps, warnings)

    if not (stance <= crouch < release <= landing):
        warnings.append(
            "Ordre des phases incohérent : la détection est probablement "
            "peu fiable sur ce clip."
        )
    return Phases(stance, crouch, release, landing, jump_peak, warnings)


def _local_maxima(y: np.ndarray, min_prominence: float) -> list[int]:
    """Maxima locaux dont la proéminence (vs vallées voisines) dépasse le seuil."""
    peaks: list[int] = []
    for i in range(1, len(y) - 1):
        if y[i] >= y[i - 1] and y[i] > y[i + 1]:
            left_min = np.nanmin(y[: i + 1])
            right_min = np.nanmin(y[i:])
            if y[i] - max(left_min, right_min) >= min_prominence:
                peaks.append(i)
    return peaks


def _detect_release(sig: PhaseSignals, fps: float, warnings: list[str]) -> int:
    """Release = pic de hauteur du poignet, affiné par l'extension max du coude.

    Dans une fenêtre de ±0.15 s autour du pic du poignet, on choisit la frame
    qui maximise (hauteur poignet normalisée + extension coude normalisée) :
    c'est là que la vitesse angulaire du coude s'annule (extension maximale).
    """
    wh = sig.wrist_height
    span = float(np.nanmax(wh) - np.nanmin(wh))
    if span <= 1e-9:
        raise ValueError("Poignet immobile : pas de tir détectable dans ce clip.")
    peaks = _local_maxima(wh, min_prominence=0.35 * span)
    if not peaks:
        peaks = [int(np.nanargmax(wh))]
    # Plusieurs pics de poignet séparés de plus d'une seconde = plusieurs tirs.
    distinct = [peaks[0]]
    for p in peaks[1:]:
        if sig.t[p] - sig.t[distinct[-1]] > 1.0:
            distinct.append(p)
    if len(distinct) > 1:
        warnings.append(
            f"{len(distinct)} tirs détectés dans le clip : seul le premier est analysé."
        )
    peak = distinct[0]

    half_win = max(1, int(round(0.15 * fps)))
    lo, hi = max(0, peak - half_win), min(len(wh), peak + half_win + 1)
    wh_win = wh[lo:hi]
    el_win = sig.elbow_angle[lo:hi]
    wh_n = _normalize(wh_win)
    el_n = _normalize(el_win)
    score = np.where(np.isnan(wh_n), -np.inf, wh_n) + np.where(np.isnan(el_n), 0, el_n)
    return lo + int(np.argmax(score))


CROUCH_WINDOW_S = 1.5  # la crouch d'un tir précède la release de ~0.3-0.8 s


def _detect_crouch(sig: PhaseSignals, release: int, fps: float, warnings: list[str]) -> int:
    """Crouch = flexion maximale des genoux (minimum de l'angle) avant la release.

    La recherche est bornée à CROUCH_WINDOW_S avant la release : plus tôt
    dans le clip, une flexion profonde est en général un ramassage de ballon
    ou un dribble bas, pas la préparation du tir.
    """
    lo = max(0, release - int(round(CROUCH_WINDOW_S * fps)))
    segment = sig.knee_angle[lo:release]
    if len(segment) == 0 or np.all(np.isnan(segment)):
        warnings.append("Flexion des genoux introuvable avant la release.")
        return max(0, release - 1)
    return lo + int(np.nanargmin(segment))


def _detect_stance(sig: PhaseSignals, crouch: int, fps: float) -> int:
    """Stance = dernier instant stable avant la flexion.

    On cherche, avant la crouch, la dernière frame où la vitesse verticale des
    hanches reste sous 15 % de la vitesse maximale du clip pendant ~0.1 s.
    """
    if crouch <= 1:
        return 0
    v = np.gradient(sig.hip_height, sig.t)
    speed = np.abs(v[:crouch])
    vmax = float(np.nanmax(np.abs(v)))
    if vmax <= 1e-9:
        return 0
    threshold = 0.15 * vmax
    run_needed = max(1, int(round(0.1 * fps)))
    run = 0
    stance = 0
    for i in range(crouch):
        if speed[i] < threshold:
            run += 1
            if run >= run_needed:
                stance = i
        else:
            run = 0
    return stance


def _detect_landing(
    sig: PhaseSignals, release: int, crouch: int, fps: float, warnings: list[str]
) -> tuple[int, int]:
    """Landing = retour des chevilles au sol après l'apex du saut.

    Renvoie (jump_peak, landing). La ligne de sol de référence est la hauteur
    médiane des chevilles avant la crouch.
    """
    ah = sig.ankle_height
    n = len(ah)
    after = ah[release:]
    if len(after) < 2 or np.all(np.isnan(after)):
        warnings.append("Fin de clip trop tôt : atterrissage non observé.")
        return release, n - 1
    jump_peak = release + int(np.nanargmax(after))
    baseline = float(np.nanmedian(ah[: max(crouch, 1)]))
    apex_h = float(ah[jump_peak])
    hip_span = float(np.nanmax(sig.hip_height) - np.nanmin(sig.hip_height))
    if apex_h - baseline < 0.10 * max(hip_span, 1e-9):
        warnings.append("Saut très faible ou absent : atterrissage approximatif.")

    seg = ah[jump_peak:]
    # Première frame où les chevilles reviennent près du sol…
    near_ground = np.where(seg <= baseline + 0.15 * max(apex_h - baseline, 1e-9))[0]
    if len(near_ground):
        return jump_peak, jump_peak + int(near_ground[0])
    # …sinon premier minimum local après l'apex.
    for i in range(1, len(seg) - 1):
        if seg[i] <= seg[i - 1] and seg[i] < seg[i + 1]:
            return jump_peak, jump_peak + i
    warnings.append("Fin de clip trop tôt : atterrissage non observé.")
    return jump_peak, n - 1


def _normalize(y: np.ndarray) -> np.ndarray:
    span = np.nanmax(y) - np.nanmin(y)
    if not np.isfinite(span) or span <= 1e-12:
        return np.zeros_like(y)
    return (y - np.nanmin(y)) / span


def detect_shooting_side(seq: PoseSequence) -> str:
    """Détection automatique du côté de tir : bras le plus haut à la release.

    Heuristique : on compare la hauteur image maximale atteinte par chaque
    poignet, rapportée à la hauteur des épaules (le poignet du bras de tir
    monte nettement plus haut).
    """
    heights = seq.image_heights()
    shoulder = np.nanmean(
        (heights[:, lm.LEFT_SHOULDER] + heights[:, lm.RIGHT_SHOULDER]) / 2
    )
    left = np.nanmax(heights[:, lm.LEFT_WRIST]) - shoulder
    right = np.nanmax(heights[:, lm.RIGHT_WRIST]) - shoulder
    return "right" if right >= left else "left"
