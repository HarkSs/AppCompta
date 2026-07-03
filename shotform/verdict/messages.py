"""Textes de feedback pré-rédigés (français).

Chaque métrique « à corriger » a deux conseils : valeur trop basse ("low")
et trop haute ("high"). Les templates reçoivent : value (mesure), lo, hi
(plage pro p10-p90) et unit. Ton direct, concret, chiffré.
"""
from __future__ import annotations

STATUS_LABELS = {
    "bon": "Bon",
    "limite": "Limite",
    "a_corriger": "À corriger",
    "incertain": "Incertain",
    "sans_reference": "Sans référence",
}

# {value}, {lo}, {hi} sont formatés avant insertion (voir format_value).
ADVICE: dict[str, dict[str, str]] = {
    "knee_flexion_shooting": {
        "low": (
            "Ton genou côté tir est très fléchi ({value}) à la crouch, les pros "
            "sont entre {lo} et {hi}. Une flexion trop profonde ralentit la "
            "montée : reste plus tonique, descends un peu moins bas."
        ),
        "high": (
            "Ton genou côté tir est à {value} à la crouch, les pros descendent "
            "entre {lo} et {hi}. Fléchis davantage les jambes : c'est d'elles "
            "que vient la puissance du tir, pas des bras."
        ),
    },
    "knee_flexion_opposite": {
        "low": (
            "Ton genou opposé est très fléchi ({value}) par rapport aux pros "
            "({lo} à {hi}). Équilibre la flexion des deux jambes pour une "
            "poussée symétrique."
        ),
        "high": (
            "Ton genou opposé reste trop tendu ({value}, pros entre {lo} et "
            "{hi}). Fléchis les deux jambes de la même façon pour monter droit."
        ),
    },
    "trunk_lean": {
        "low": (
            "Ton buste est très droit ({value}) à la crouch, les pros penchent "
            "légèrement entre {lo} et {hi}. Une petite inclinaison vers l'avant "
            "aide à engager les hanches."
        ),
        "high": (
            "Ton buste penche de {value} à la crouch, les pros restent entre "
            "{lo} et {hi}. Redresse-toi : un buste trop penché déséquilibre le "
            "tir vers l'avant."
        ),
    },
    "elbow_angle": {
        "low": (
            "Ton coude est à {value} à la release, les shooters d'élite sont "
            "entre {lo} et {hi}. Ouvre davantage ton angle de coude au moment "
            "du lâcher et pense à finir l'extension complètement."
        ),
        "high": (
            "Ton coude est à {value} à la release, les shooters d'élite sont "
            "entre {lo} et {hi}. Rapproche ton coude de ton corps et arme le "
            "ballon plus près de ta ligne d'épaule."
        ),
    },
    "forearm_elevation": {
        "low": (
            "Ton avant-bras ne monte qu'à {value} au-dessus de l'horizontale à "
            "la release (pros : {lo} à {hi}). Tire plus vers le haut : vise la "
            "sortie de balle haute, pas devant toi."
        ),
        "high": (
            "Ton avant-bras est très vertical ({value}, pros entre {lo} et "
            "{hi}). Tu tires trop « en cloche » : allonge légèrement ta "
            "trajectoire vers le cercle."
        ),
    },
    "body_alignment": {
        "low": (
            "Ton alignement épaule-hanche-genou est de {value} à la release "
            "(pros : {lo} à {hi}). Ton corps est cassé au moment du lâcher : "
            "pousse jusqu'à l'extension complète, épaule au-dessus de la hanche."
        ),
        "high": (
            "Ton alignement épaule-hanche-genou dépasse la plage pro ({value}, "
            "pros : {lo} à {hi}). Tu es en hyperextension : reste gainé et "
            "vertical au sommet du saut."
        ),
    },
    "elbow_lateral_offset": {
        "low": (
            "Ton coude est très verrouillé dans l'axe ({value}, pros entre {lo} "
            "et {hi}). C'est plutôt une qualité — vérifie simplement que ton "
            "épaule reste relâchée."
        ),
        "high": (
            "Ton coude s'ouvre de {value} hors du plan de tir (pros : {lo} à "
            "{hi}) — c'est le fameux « chicken wing ». Garde le coude sous le "
            "ballon, aligné épaule-poignet-cercle."
        ),
    },
    "release_height": {
        "low": (
            "Tu lâches le ballon à {value} au-dessus de la tête (pros : {lo} à "
            "{hi}). Monte ton point de release : tends complètement le bras "
            "au-dessus du front, pas devant la poitrine."
        ),
        "high": (
            "Ton point de release est très haut ({value}, pros entre {lo} et "
            "{hi}). Vérifie que tu ne tires pas en arrière de la tête, au "
            "détriment du rythme."
        ),
    },
    "crouch_to_release_time": {
        "low": (
            "Ta montée dure {value} entre la crouch et la release (pros : {lo} "
            "à {hi}). C'est très rapide : assure-toi de rester coordonné, "
            "jambes puis bras."
        ),
        "high": (
            "Ta montée dure {value} entre la crouch et la release, les pros "
            "sont entre {lo} et {hi}. Gagne en explosivité : enchaîne flexion "
            "et extension sans temps mort, le tir part dans la montée."
        ),
    },
    "jump_symmetry": {
        "low": (
            "Ton saut est parfaitement symétrique ({value}, pros : {lo} à "
            "{hi}). Rien à corriger ici."
        ),
        "high": (
            "Tes chevilles ont un écart de hauteur de {value} au sommet du "
            "saut (pros : {lo} à {hi}). Tu sautes déséquilibré : pousse "
            "également sur les deux jambes et atterris au même endroit."
        ),
    },
}

GOOD_MESSAGE = "{label} : {value} — dans la plage pro ({lo} à {hi})."
BORDERLINE_MESSAGE = (
    "{label} : {value} — juste en dehors de la plage pro ({lo} à {hi}), à surveiller."
)
UNRELIABLE_MESSAGE = (
    "{label} : mesure incertaine ({reasons}), non prise en compte dans le score."
)
NO_REFERENCE_MESSAGE = "{label} : pas de plage de référence disponible."

FALLBACK_NOTICE = (
    "⚠ Référentiel de repli (repères de coaching génériques) : construisez le "
    "référentiel pro avec `python -m shotform build-reference pro_clips/` pour "
    "des plages issues de vrais tirs d'élite."
)


def format_value(value: float, unit: str) -> str:
    """Formate une valeur avec son unité pour les textes français."""
    if unit == "°":
        return f"{value:.0f}°"
    if unit == "s":
        return f"{value:.2f} s"
    # ratios normalisés par la longueur du tronc
    return f"{value:.2f} ×tronc"


def advice_for(metric: str, direction: str, value: str, lo: str, hi: str) -> str:
    """Conseil « à corriger » pour une métrique, selon le sens de l'écart."""
    template = ADVICE[metric]["high" if direction == "high" else "low"]
    return template.format(value=value, lo=lo, hi=hi)
