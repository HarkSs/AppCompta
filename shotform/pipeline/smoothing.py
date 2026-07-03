"""Lissage des trajectoires par filtre de Savitzky-Golay (NumPy pur).

On implémente le filtre directement (pas de dépendance SciPy) : les
coefficients sont obtenus par moindres carrés sur une fenêtre glissante
centrée, ce qui préserve la position des extrema mieux qu'une moyenne
mobile — important pour la détection des phases.
"""
from __future__ import annotations

import numpy as np


def savgol_coefficients(window: int, polyorder: int) -> np.ndarray:
    """Coefficients du filtre de Savitzky-Golay évalué au centre de la fenêtre."""
    if window % 2 == 0 or window < 3:
        raise ValueError("window doit être impair et >= 3")
    if polyorder >= window:
        raise ValueError("polyorder doit être < window")
    half = window // 2
    x = np.arange(-half, half + 1, dtype=float)
    # Matrice de Vandermonde ; la ligne 0 de la pseudo-inverse évalue le
    # polynôme ajusté en x=0 (centre de la fenêtre).
    a = np.vander(x, polyorder + 1, increasing=True)
    return np.linalg.pinv(a)[0]


def savgol_filter(values: np.ndarray, window: int, polyorder: int = 3) -> np.ndarray:
    """Applique le filtre le long du premier axe. Les NaN sont préservés.

    Les bords sont traités par réflexion du signal. Si le signal est plus
    court que la fenêtre, la fenêtre est réduite au plus grand impair possible.
    """
    values = np.asarray(values, dtype=float)
    n = values.shape[0]
    if n < 3:
        return values.copy()
    window = min(window, n if n % 2 == 1 else n - 1)
    if window < polyorder + 2:
        return values.copy()
    if window % 2 == 0:
        window -= 1
    coeffs = savgol_coefficients(window, polyorder)
    half = window // 2

    flat = values.reshape(n, -1)
    nan_mask = np.isnan(flat)
    filled = _interpolate_nan(flat)
    out = np.empty_like(filled)
    x_win = np.arange(window)
    for j in range(filled.shape[1]):
        col = filled[:, j]
        out[half : n - half, j] = np.convolve(col, coeffs[::-1], mode="valid")
        # Bords : ajustement polynomial sur la première/dernière fenêtre
        # (équivalent du mode "interp" de SciPy) — préserve exactement les
        # polynômes de degré <= polyorder jusqu'aux extrémités.
        p_first = np.polyfit(x_win, col[:window], polyorder)
        out[:half, j] = np.polyval(p_first, x_win[:half])
        p_last = np.polyfit(x_win, col[-window:], polyorder)
        out[n - half :, j] = np.polyval(p_last, x_win[half + 1 :])
    out[nan_mask] = np.nan
    return out.reshape(values.shape)


def _interpolate_nan(flat: np.ndarray) -> np.ndarray:
    """Interpole linéairement les NaN colonne par colonne (bords : plus proche voisin)."""
    out = flat.copy()
    idx = np.arange(flat.shape[0])
    for j in range(flat.shape[1]):
        col = out[:, j]
        good = ~np.isnan(col)
        if not good.any():
            out[:, j] = 0.0
        elif not good.all():
            out[:, j] = np.interp(idx, idx[good], col[good])
    return out


def interpolate_gaps(values: np.ndarray, present: np.ndarray, max_gap: int) -> np.ndarray:
    """Interpole les frames manquantes intérieures de longueur <= max_gap.

    `values` : (T, ...) ; `present` : (T,) booléen. Les trous plus longs que
    max_gap et les bords restent NaN (mesure non fiable plutôt que fausse).
    """
    values = np.asarray(values, dtype=float)
    present = np.asarray(present, dtype=bool)
    out = values.copy()
    t = len(present)
    if present.all() or not present.any():
        return out
    idx = np.arange(t)
    fillable = np.zeros(t, dtype=bool)
    i = 0
    while i < t:
        if present[i]:
            i += 1
            continue
        j = i
        while j < t and not present[j]:
            j += 1
        # trou [i, j) ; intérieur seulement, et pas trop long
        if i > 0 and j < t and (j - i) <= max_gap:
            fillable[i:j] = True
        i = j
    if fillable.any():
        flat = out.reshape(t, -1)
        good = present
        for c in range(flat.shape[1]):
            col = flat[:, c]
            col[fillable] = np.interp(idx[fillable], idx[good], col[good])
        out = flat.reshape(values.shape)
    return out
