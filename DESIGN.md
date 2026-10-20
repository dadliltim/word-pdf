---
version: alpha
colors:
  background: "#EAF0F5"
  paper: "#FFFFFF"
  ink: "#19334A"
  primary: "#155D83"
  muted: "#506477"
  error: "#A12431"
typography:
  body:
    fontFamily: "Segoe UI, sans-serif"
  reference:
    fontFamily: "Consolas, monospace"
rounded:
  control: "6px"
  panel: "10px"
omitted:
  - section: spacing
    reason: "Desktop grid and web layout geometry are documented in the Layout section."
---

## Overview

Outil de classement documentaire français pour un poste Windows interne, disponible en bureau et dans le navigateur. Une seule surface de travail, inspirée d'une fiche de circulation : source, deux destinations, référence puis document choisi. La référence et les noms de sortie sont la signature visuelle ; pas de statistiques inventées.

## Colors

Le bleu ardoise donne une hiérarchie de bureau documentaire. `word_pdf/theme.json` est la source runtime canonique des six couleurs ci-dessus. Adaptateurs : `THEME` dans `gui.py` et `/theme.css` généré par `web.py` vers les propriétés CSS de `static/app.css`. Les valeurs ne sont pas recopiées dans ces adaptateurs. Les couleurs auxiliaires de bordure, succès et défilement sont définies dans `static/app.css`. Les erreurs sont toujours accompagnées de texte. Un seul thème clair, sans ressources distantes.

## Typography

Segoe UI est la police système Windows utilisée pour les titres et contrôles, avec Arial/sans-serif de remplacement sur le web. La référence reste un texte sélectionnable dans un champ natif, en Consolas/monospace dans le navigateur. Aucun téléchargement de police.

## Layout

Le bureau conserve sa grille redimensionnable, marges de 24 pixels et fenêtre minimale de 660 × 640 pixels. Le web utilise une colonne de dossiers de 310 pixels et une colonne de travail fluide, largeur maximale de 1320 pixels. Sous 700 pixels, les colonnes se suivent dans le défilement naturel de la page. Seul le tableau possède un défilement interne, avec pagination serveur de 25 résultats. Aucune hauteur de viewport imposée au formulaire.

## Elevation & Depth

Pas d'ombres artificielles : bordures des contrôles Tk et bordures CSS discrètes, sans élévation décorative.

## Shapes

Contrôles rectangulaires natifs sur le bureau. Sur le web, panneaux de rayon 10 pixels et boutons/champs de rayon 6 pixels, sans popup personnalisé.

## Components

`Application._button` possède les actions, `_message` le statut persistant, `_work` le blocage des doubles soumissions. `ttk.Entry` possède les champs, `ttk.Treeview` la sélection simple, `filedialog.askdirectory` le choix de dossier natif Windows. Le système possède la géométrie des dialogues et des barres de défilement. Pas d'équivalent existant : dépôt initialement vide.

Le web réutilise `core.py` pour les règles de fichiers. Les propriétaires des formulaires, cases à cocher, statuts, pagination et téléchargements sont documentés dans `UX-CONTRACT.md`. Les styles globaux de défilement appartiennent à `static/app.css` avec tokens thumb/track/hover/active, fallback WebKit et forced-colors. Seuls les spinners tournent ; reduced-motion supprime animations et transitions.

La sélection web utilise désormais des cases à cocher natives, avec compteur global et sélection de la page. `batch-dialog` reprend le rayon des panneaux, les boutons et les couleurs existants ; son contenu défile naturellement dans une hauteur maximale de 85vh. Le bilan du lot utilise des blocs de résultats avec les mêmes chemins et boutons de téléchargement, sans nouvelle palette.

## Do's and Don'ts

Conserver les champs après une erreur, afficher les chemins exportés après réussite, désactiver les actions pendant une opération. Ne jamais écraser une sortie ni modifier un original. La recherche est explicite et locale ; aucune référence ni aucun chemin n'est stocké dans une URL ou envoyé sur le réseau. Tester l'accessibilité avec les outils Windows avant diffusion ; aucune conformité lecteur d'écran n'est revendiquée par inspection du code.
