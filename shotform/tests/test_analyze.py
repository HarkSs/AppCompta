"""Intégration : pipeline complet sur une séquence synthétique (sans MediaPipe)."""
from __future__ import annotations

import json

from shotform.analyze import analyze_sequence
from shotform.verdict.rules import FALLBACK_PATH


class TestAnalyzeSequence:
    def test_end_to_end_report(self, shot_sequence):
        seq, truth = shot_sequence
        analysis = analyze_sequence(seq, shooting_side="right", reference_path=FALLBACK_PATH)

        assert analysis.shooting_side == "right"
        assert analysis.side_source == "user"
        p = analysis.phases
        assert p.stance <= p.crouch < p.release <= p.landing
        assert abs(p.release - truth["release"]) <= 5

        # Toutes les métriques sont présentes et le score est calculable.
        assert analysis.verdict.score is not None
        assert 0.0 <= analysis.verdict.score <= 100.0
        assert analysis.verdict.reference_type == "fallback"

        report = analysis.report()
        # Le rapport doit être strictement JSON-sérialisable.
        encoded = json.dumps(report, ensure_ascii=False)
        assert "phases" in report and "verdict" in report
        assert report["quality"]["orientation"] == "face"
        assert set(report["phases"]) == {"stance", "crouch", "release", "landing"}
        assert encoded  # non vide

    def test_auto_side_detection_with_warning(self, shot_sequence):
        seq, _ = shot_sequence
        analysis = analyze_sequence(seq)
        assert analysis.shooting_side == "right"
        assert analysis.side_source == "auto"
        assert any("automatique" in w for w in analysis.warnings)

    def test_wrong_user_side_flagged(self, shot_sequence):
        seq, _ = shot_sequence
        analysis = analyze_sequence(seq, shooting_side="left")
        assert analysis.shooting_side == "left"  # le choix utilisateur prime
        assert any("--side" in w for w in analysis.warnings)
