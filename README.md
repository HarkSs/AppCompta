# MaCompta

Application de comptabilité légère pour entrepreneurs individuels en France.

## Installation

1. Créez un environnement virtuel Python 3.11+ et installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
2. Lancez l'application :
   ```bash
   python main.py
   ```

## Packaging Windows (.exe)

Un script batch est fourni pour générer un exécutable avec PyInstaller :

```bat
build_exe.bat
```

Le binaire `MaCompta.exe` est produit dans le dossier `dist/`. L'application conserve ses données dans `Documents/MaCompta/donnees.db` et les backups dans `Documents/MaCompta/backups/`.

## Fonctionnalités principales

- Gestion des transactions (recettes/dépenses) avec catégories personnalisables
- Import CSV bancaire avec mapping des colonnes
- Exports CSV et génération du livre des recettes en PDF simple
- Rapports basiques (totaux par période, par catégorie)
- Sauvegarde/restauration via fichiers ZIP (base et paramètres)
- Paramètres pour la devise, le régime, les seuils TVA et la tolérance de rapprochement

## Sauvegarde et restauration

- Les sauvegardes automatiques sont stockées dans `Documents/MaCompta/backups/` sous forme de fichiers `backup-YYYYMMDD-HHMM.zip`.
- Pour restaurer, utilisez l'écran Paramètres ou copiez `donnees.db` et `metadata.json` depuis l'archive.

## Import CSV

1. Exportez vos transactions bancaires en CSV.
2. Dans l'écran Transactions, utilisez l'assistant d'import (à venir) ou le service en ligne de commande.
3. Mappez les colonnes date/libellé/montant. Option pour inverser le signe si nécessaire.

## Limites connues

- Module de facturation en lecture seule (v2).
- TVA non gérée dans la version actuelle.
- Requiert PySide6 et ReportLab pour le rendu PDF.

## Roadmap v2

- Factures PDF numérotées avec statut payé/impayé et lien transaction.
- Gestion TVA (taux multiples, rapport TVA par période, exports enrichis).
- Plan comptable léger avec mapping catégories → comptes comptables.

## Jeu d'essai

Un fichier `data/sample.db` est fourni avec quelques transactions ainsi qu'un CSV `data/exemple_transactions.csv` pour tester l'import.

## Tests

```bash
pytest
```

## Licence

Projet distribué sous licence MIT. Voir `LICENSE`.
