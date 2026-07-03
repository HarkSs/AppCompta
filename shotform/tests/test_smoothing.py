"""Filtre de Savitzky-Golay et interpolation des trous."""
from __future__ import annotations

import numpy as np
import pytest

from shotform.pipeline.smoothing import interpolate_gaps, savgol_coefficients, savgol_filter


class TestSavgol:
    def test_coefficients_sum_to_one(self):
        assert savgol_coefficients(11, 3).sum() == pytest.approx(1.0)

    def test_polynomial_preserved_exactly(self):
        # Un polynôme de degré <= polyorder doit traverser le filtre inchangé.
        x = np.linspace(0, 1, 50)
        y = 2.0 + 3.0 * x - 1.5 * x**2 + 0.7 * x**3
        out = savgol_filter(y, window=11, polyorder=3)
        assert out == pytest.approx(y, abs=1e-9)

    def test_reduces_noise(self):
        rng = np.random.default_rng(42)
        x = np.linspace(0, 2 * np.pi, 200)
        clean = np.sin(x)
        noisy = clean + rng.normal(0, 0.1, x.shape)
        out = savgol_filter(noisy, window=15, polyorder=3)
        assert np.std(out - clean) < np.std(noisy - clean) * 0.6

    def test_multidimensional(self):
        y = np.zeros((50, 3, 2))
        y[:, 0, 0] = np.linspace(0, 1, 50)
        out = savgol_filter(y, window=9)
        assert out.shape == y.shape
        assert out[:, 0, 0] == pytest.approx(y[:, 0, 0], abs=1e-9)

    def test_short_signal_passthrough(self):
        y = np.array([1.0, 2.0])
        assert savgol_filter(y, window=11).tolist() == [1.0, 2.0]

    def test_nan_preserved(self):
        y = np.linspace(0, 1, 30)
        y[10] = np.nan
        out = savgol_filter(y, window=7)
        assert np.isnan(out[10])
        assert np.isfinite(np.delete(out, 10)).all()


class TestInterpolateGaps:
    def test_short_interior_gap_filled(self):
        values = np.array([0.0, 1.0, np.nan, np.nan, 4.0, 5.0])
        present = np.array([True, True, False, False, True, True])
        out = interpolate_gaps(values, present, max_gap=3)
        assert out == pytest.approx([0, 1, 2, 3, 4, 5])

    def test_long_gap_left_nan(self):
        values = np.array([0.0, np.nan, np.nan, np.nan, np.nan, 5.0])
        present = np.array([True, False, False, False, False, True])
        out = interpolate_gaps(values, present, max_gap=2)
        assert np.isnan(out[1:5]).all()

    def test_edge_gap_left_nan(self):
        values = np.array([np.nan, np.nan, 2.0, 3.0])
        present = np.array([False, False, True, True])
        out = interpolate_gaps(values, present, max_gap=5)
        assert np.isnan(out[:2]).all()
        assert out[2:] == pytest.approx([2.0, 3.0])
