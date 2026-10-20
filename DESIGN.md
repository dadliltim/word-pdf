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
  study:
    fontFamily: "Georgia, Times New Roman, serif"
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

Le bandeau blanc de 100px possède trois colonnes équilibrées : Référence à gauche, signature centrée « Etude Maitre Souad CHABAB » et « By Hatim DALIL » en dessous, version à droite. La signature adopte Georgia en 25px/400, une signature secondaire de 10px avec espacement de lettres, et deux traits fins issus de la couleur de bordure existante. Cette exception typographique évoque l'en-tête d'une étude ; les formulaires conservent Segoe UI. Sous 960px, elle passe sur une seconde ligne centrée en 21px pour éviter tout chevauchement. Aucun téléchargement de police ni nouvelle couleur.

Le bureau conserve sa grille redimensionnable, marges de 24 pixels et fenêtre minimale de 660 × 640 pixels. Le web utilise une colonne de dossiers de 310 pixels et une colonne de travail fluide, largeur maximale de 1320 pixels. Sous 700 pixels, les colonnes se suivent dans le défilement naturel de la page. Seul le tableau possède un défilement interne, avec pagination serveur de 25 résultats. Aucune hauteur de viewport imposée au formulaire.

## Elevation & Depth

Pas d'ombres artificielles : bordures des contrôles Tk et bordures CSS discrètes, sans élévation décorative.

## Shapes

Contrôles rectangulaires natifs sur le bureau. Sur le web, panneaux de rayon 10 pixels et boutons/champs de rayon 6 pixels, sans popup personnalisé.

## Components

`Application._button` possède les actions, `_message` le statut persistant, `_work` le blocage des doubles soumissions. `ttk.Entry` possède les champs, `ttk.Treeview` la sélection simple, `filedialog.askdirectory` le choix de dossier natif Windows. Le système possède la géométrie des dialogues et des barres de défilement. Pas d'équivalent existant : dépôt initialement vide.

Le web réutilise `core.py` pour les règles de fichiers. Les propriétaires des formulaires, cases à cocher, statuts, pagination et téléchargements sont documentés dans `UX-CONTRACT.md`. Les styles globaux de défilement appartiennent à `static/app.css` avec tokens thumb/track/hover/active, fallback WebKit et forced-colors. Seuls les spinners tournent ; reduced-motion supprime animations et transitions.

La sélection web utilise désormais des cases à cocher natives, avec compteur global et sélection de la page. `batch-dialog` reprend le rayon des panneaux, les boutons et les couleurs existants ; son contenu défile naturellement dans une hauteur maximale de 85vh. Le bilan du lot utilise des blocs de résultats avec les mêmes chemins et boutons de téléchargement, sans nouvelle palette.

La recherche directe est désormais prioritaire, avec un titre de 29px sur une ligne et une mise en page compacte. Le panneau de saisie libre est un `details` fermé par défaut, accessible juste après le champ de recherche, de couleur soft et de rayon de contrôle. Son textarea natif garde une hauteur suffisante et son défilement système ; la proposition modifiable utilise le même champ texte que la recherche. La mention de traitement local et l'étape de vérification font partie du contenu permanent, sans habillage de chat ou promesse d'IA générative. Après utilisation de la proposition, le panneau se replie et la recherche reprend le focus.

Un compteur de sélection est placé près des cases de la page, avec une pastille primaire lorsque la sélection est non vide. Les noms de fichiers utilisent un corps de 13px. Le trait intérieur de la ligne cochée renforce la sélection sans communiquer par la couleur seule. La progression native du lot mesure le nombre de documents traités, succès et erreurs compris, et conserve le bilan explicite par fichier. La hauteur naturelle des formulaires et le défilement propre au tableau restent indépendants.

## Do's and Don'ts

Conserver les champs après une erreur, afficher les chemins exportés après réussite, désactiver les actions pendant une opération. Ne jamais écraser une sortie ni modifier un original. La recherche est explicite et locale ; aucune référence ni aucun chemin n'est stocké dans une URL ou envoyé sur le réseau. Tester l'accessibilité avec les outils Windows avant diffusion ; aucune conformité lecteur d'écran n'est revendiquée par inspection du code.
