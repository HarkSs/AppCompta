# ShotForm — analyse biomécanique de tir au basket (phase 1)

Moteur d'analyse 100 % local : une vidéo de tir (smartphone, 2-10 s, un seul
tir) est comparée à un référentiel construit à partir de tirs de shooters
d'élite, et un moteur de règles déterministe (aucun LLM, aucun appel réseau)
produit un score /100 et des conseils chiffrés en français.

## Installation

```bash
python -m venv .venv && source .venv/bin/activate   # Python 3.11+
pip install -r shotform/requirements.txt
# Une seule fois (ensuite tout fonctionne hors ligne / en mode avion) :
python -m shotform.scripts.download_models
```

## Utilisation

```bash
# Analyser un tir (le côté est détecté automatiquement si --side est omis)
python -m shotform analyze video.mp4 --side right --out report/
# -> report/report.json, report/summary.txt, report/annotated.mp4

# Construire le référentiel pro depuis un dossier de clips (Curry, Booker…)
python -m shotform build-reference pro_clips/ --review --side right
# -> shotform/reference/reference.json
# --review génère pro_clips/review/<clip>_annotated.mp4 pour CHAQUE clip :
#    vérifiez visuellement squelette + phases avant d'adopter le référentiel.
# --side right : écarte les clips où le tireur détecté est du côté opposé
#    (typiquement une autre personne dans le champ).
# --exclude crouch_to_release_time : à utiliser si les clips sont en ralenti.

# Préparer les clips depuis des vidéos brutes :
python -m shotform.scripts.split_clips compilation.mp4 pro_clips/   # compilation avec changements de plan
python -m shotform.scripts.split_shots seance.mp4 pro_clips/        # plan-séquence d'entraînement (1 clip par tir)

# Démo pas-à-pas de bout en bout
python -m shotform.scripts.demo chemin/vers/tir.mp4 right

# Modèle plus rapide (moins précis) si la machine est lente
python -m shotform analyze video.mp4 --model full
```

Tant que `reference.json` n'existe pas, l'analyse utilise
`reference_fallback.json` (repères de coaching génériques), clairement marqué
« référentiel de repli » dans les rapports. Quand le référentiel pro existe
mais qu'une métrique manque d'échantillons (n < 5), la plage de repli est
utilisée pour cette métrique et signalée « (plage de repli) » dans le conseil.

Le `reference.json` fourni a été construit sur 37 tirs d'entraînement de
Stephen Curry (vidéos à vitesse réelle) ; chaque clip est passé par un
garde-fou de plausibilité (poignet au-dessus de la tête et avant-bras vers le
haut à la release) qui écarte les détections accrochées sur un dribble, une
passe ou une autre personne.

Note vidéos : si `ffmpeg` est présent sur la machine, les vidéos produites
(annotées, clips découpés) sont automatiquement réencodées en H.264, lisible
dans les navigateurs ; sinon elles restent en MPEG-4 « mp4v » (VLC les lit).

## Comment ça marche

1. **Extraction** (`pipeline/extractor.py`) — MediaPipe PoseLandmarker
   (Tasks, mode VIDEO, modèle *heavy*) fournit les 33 **world landmarks 3D**
   par frame (mètres, origine au centre des hanches). Les trajectoires sont
   lissées par un filtre de Savitzky-Golay implémenté en NumPy pur.
2. **Phases** (`pipeline/phases.py`) — détection de *stance* (stabilité des
   hanches), *crouch* (flexion max des genoux), *release* (pic de hauteur du
   poignet + extension max du coude), *landing* (retour des chevilles au sol).
   Les événements temporels utilisent les hauteurs **image** (les world
   landmarks étant centrés hanches, le mouvement vertical global y est
   invisible) ; les angles utilisent les coordonnées **monde 3D**.
3. **Angles** (`pipeline/angles.py`) — tous les angles sont calculés en 3D,
   donc quasi invariants à l'angle de caméra (testé : une rotation de 40° du
   squelette ne change pas les métriques).
4. **Qualité** (`pipeline/quality.py`) — orientation du tireur (face,
   trois-quarts, profil, dos) estimée via le vecteur épaules ; chaque
   métrique reçoit une confiance basée sur la visibilité de ses landmarks à
   la phase de mesure. Les mesures incertaines sont **exclues du score** et
   listées comme telles, avec une recommandation de prise de vue.
5. **Verdict** (`verdict/rules.py`) — chaque métrique fiable est comparée à
   la plage [p10, p90] du référentiel : *bon* / *limite* / *à corriger*, avec
   écart chiffré et conseil pré-rédigé (`verdict/messages.py`). Score global
   /100 pondéré (pondération justifiée en commentaire dans `rules.py` :
   le coude et la release pèsent plus que la symétrie du saut).

## Métriques

| Phase   | Métrique | Détail |
|---------|----------|--------|
| crouch  | `knee_flexion_shooting` / `knee_flexion_opposite` | angle hanche-genou-cheville |
| crouch  | `trunk_lean` | inclinaison épaules-hanches vs verticale |
| release | `elbow_angle` | épaule-coude-poignet |
| release | `forearm_elevation` | coude→poignet vs plan horizontal |
| release | `body_alignment` | épaule-hanche-genou côté tir (180° = aligné) |
| release | `elbow_lateral_offset` | sortie du coude hors du plan épaule-poignet-verticale (« chicken wing ») |
| release | `release_height` | hauteur poignet-nez normalisée par la longueur du tronc |
| timing  | `crouch_to_release_time` | explosivité |
| timing  | `jump_symmetry` | écart de hauteur des chevilles à l'apex, normalisé tronc |

## Tests

```bash
pytest shotform/tests
```

La géométrie est testée sur des squelettes synthétiques aux angles connus, la
détection de phases sur des trajectoires synthétiques, et le pipeline complet
(hors MediaPipe) sur un tir synthétique animé. Aucun test ne requiert
MediaPipe/OpenCV : ces imports sont paresseux.

## Limites connues

- **Profondeur mono-caméra.** La coordonnée Z des world landmarks est
  *estimée* par le modèle, pas mesurée : les angles impliquant la profondeur
  (chicken wing, orientation) sont moins précis qu'un système multi-caméras.
  L'objectif < 8° d'écart entre prise de face et de 3/4 doit être validé sur
  vos propres vidéos réelles.
- **Tireur de dos.** Détection très dégradée ; l'analyse est marquée non
  fiable et une meilleure prise de vue est recommandée.
- **Verticale = verticale de l'image.** Le repère monde de MediaPipe suit la
  caméra : une caméra fortement inclinée (plongée/contre-plongée marquée)
  biaise l'inclinaison du tronc et l'élévation de l'avant-bras. Filmez à peu
  près à hauteur de poitrine.
- **Ballon non suivi.** La release est déduite de la cinématique du bras
  (pic du poignet + extension du coude), pas du départ réel du ballon ; sur
  des gestuelles atypiques l'instant peut dériver de 1-2 frames.
- **Fallback ≠ vérité.** Les plages de `reference_fallback.json` sont des
  repères de coaching génériques (notamment le coude à 85-100° à la release,
  qui correspond au repère classique du « set point ») : elles peuvent être
  en tension avec la définition cinématique de la release utilisée ici.
  Construisez le vrai référentiel dès que possible et validez chaque clip
  avec `--review`.
- **Un tir par clip.** Si plusieurs tirs sont présents, seul le premier est
  analysé (signalé dans le rapport). Détection conçue pour des clips de
  2 à 10 s.
- **Une seule personne.** Si d'autres personnes traversent le champ, la pose
  principale est analysée et un avertissement est émis ; préférez un cadrage
  sans autres joueurs.

## Phase 2

Interface graphique (designée dans Claude Design) branchée sur
`shotform.analyze.analyze_video`, qui renvoie un rapport JSON-sérialisable
complet — l'API est déjà prête pour ça.
