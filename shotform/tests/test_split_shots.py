"""Segmentation par tirs d'une vidéo continue."""
from __future__ import annotations

import numpy as np

from shotform import landmarks as lm
from shotform.scripts.split_shots import detect_shot_peaks

from .conftest import make_sequence, standing_frame


def _sequence_with_wrist_peaks(peak_times: list[float], fps: float = 30.0, duration: float = 20.0):
    n = int(duration * fps)
    world = np.repeat(standing_frame()[None], n, axis=0)
    image = np.stack(
        [0.5 + 0.15 * world[:, :, 0], 0.55 - 0.15 * world[:, :, 1]], axis=-1
    )
    # Le poignet droit monte en cloche (±0.5 s) autour de chaque tir.
    t = np.arange(n) / fps
    lift = np.zeros(n)
    for pt in peak_times:
        lift += np.clip(1.0 - np.abs(t - pt) / 0.5, 0.0, None)
    image[:, lm.RIGHT_WRIST, 1] -= 0.2 * lift
    return make_sequence(world, image=image, fps=fps)


class TestDetectShotPeaks:
    def test_finds_each_shot(self):
        seq = _sequence_with_wrist_peaks([3.0, 8.0, 14.0])
        peaks = detect_shot_peaks(seq)
        assert len(peaks) == 3
        assert [round(p / 30.0) for p in peaks] == [3, 8, 14]

    def test_close_peaks_merged(self):
        seq = _sequence_with_wrist_peaks([5.0, 5.6])
        peaks = detect_shot_peaks(seq)
        assert len(peaks) == 1

    def test_flat_signal_no_peaks(self):
        seq = _sequence_with_wrist_peaks([])
        assert detect_shot_peaks(seq) == []
