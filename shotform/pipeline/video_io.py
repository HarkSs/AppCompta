"""Écriture vidéo : finalisation H.264 pour la compatibilité lecteurs.

OpenCV écrit du MPEG-4 « mp4v », que les navigateurs et beaucoup de lecteurs
ne lisent pas. Si ffmpeg est disponible sur la machine (outil local, aucun
réseau), les vidéos produites (annotées, clips découpés) sont réencodées en
H.264 + faststart ; sinon elles restent en mp4v avec un avertissement.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_FFMPEG = shutil.which("ffmpeg")
_warned = False


def finalize_mp4(path: str | Path) -> Path:
    """Réencode un mp4 en H.264 (in place) si ffmpeg est disponible."""
    global _warned
    path = Path(path)
    if _FFMPEG is None:
        if not _warned:
            print(
                "Note : ffmpeg introuvable — vidéos écrites en mp4v "
                "(installez ffmpeg pour un H.264 lisible dans les navigateurs)."
            )
            _warned = True
        return path
    tmp = path.with_suffix(".h264.mp4")
    result = subprocess.run(
        [_FFMPEG, "-y", "-loglevel", "error", "-i", str(path),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         str(tmp)],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not tmp.is_file():
        if tmp.is_file():
            tmp.unlink()
        print(f"Note : réencodage H.264 échoué pour {path.name}, mp4v conservé.")
        return path
    tmp.replace(path)
    return path
