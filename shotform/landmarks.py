"""Index des 33 landmarks MediaPipe Pose et connexions du squelette."""
from __future__ import annotations

NOSE = 0
LEFT_EYE_INNER = 1
LEFT_EYE = 2
LEFT_EYE_OUTER = 3
RIGHT_EYE_INNER = 4
RIGHT_EYE = 5
RIGHT_EYE_OUTER = 6
LEFT_EAR = 7
RIGHT_EAR = 8
MOUTH_LEFT = 9
MOUTH_RIGHT = 10
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_PINKY = 17
RIGHT_PINKY = 18
LEFT_INDEX = 19
RIGHT_INDEX = 20
LEFT_THUMB = 21
RIGHT_THUMB = 22
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28
LEFT_HEEL = 29
RIGHT_HEEL = 30
LEFT_FOOT_INDEX = 31
RIGHT_FOOT_INDEX = 32

NUM_LANDMARKS = 33

# Connexions utilisées pour dessiner le squelette dans les vidéos annotées.
POSE_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_SHOULDER, LEFT_ELBOW),
    (LEFT_ELBOW, LEFT_WRIST),
    (RIGHT_SHOULDER, RIGHT_ELBOW),
    (RIGHT_ELBOW, RIGHT_WRIST),
    (LEFT_SHOULDER, LEFT_HIP),
    (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_HIP, LEFT_KNEE),
    (LEFT_KNEE, LEFT_ANKLE),
    (RIGHT_HIP, RIGHT_KNEE),
    (RIGHT_KNEE, RIGHT_ANKLE),
    (LEFT_ANKLE, LEFT_HEEL),
    (LEFT_HEEL, LEFT_FOOT_INDEX),
    (RIGHT_ANKLE, RIGHT_HEEL),
    (RIGHT_HEEL, RIGHT_FOOT_INDEX),
    (NOSE, LEFT_EYE),
    (NOSE, RIGHT_EYE),
)


def side_landmarks(side: str) -> dict[str, int]:
    """Renvoie les index des articulations d'un côté ("right"/"left")."""
    if side == "right":
        return {
            "shoulder": RIGHT_SHOULDER,
            "elbow": RIGHT_ELBOW,
            "wrist": RIGHT_WRIST,
            "hip": RIGHT_HIP,
            "knee": RIGHT_KNEE,
            "ankle": RIGHT_ANKLE,
        }
    if side == "left":
        return {
            "shoulder": LEFT_SHOULDER,
            "elbow": LEFT_ELBOW,
            "wrist": LEFT_WRIST,
            "hip": LEFT_HIP,
            "knee": LEFT_KNEE,
            "ankle": LEFT_ANKLE,
        }
    raise ValueError(f"Côté invalide : {side!r} (attendu 'right' ou 'left')")


def opposite_side(side: str) -> str:
    return "left" if side == "right" else "right"
