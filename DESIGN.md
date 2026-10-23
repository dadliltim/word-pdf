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

Le bleu ardoise donne une hiérarchie de bureau documentaire. `word_pdf/theme.json` est la source runtime canonique des six couleurs ci-dessus. Adaptateurs : `THEME` dans `gui.py` et `/theme.css` généré par `web.py` vers les propriétés CSS de `frontend/src/styles.css`. Les valeurs ne sont pas recopiées dans ces adaptateurs. Les couleurs auxiliaires de bordure, succès et défilement sont définies dans `frontend/src/styles.css`. Les erreurs sont toujours accompagnées de texte. Deux thèmes web, sans ressources distantes. Le mode sombre est défini par le sélecteur `:root[data-theme=dark]` dans le CSS global ; ses valeurs canoniques ne sont pas dupliquées dans le backend.

## Typography

Segoe UI est la police système Windows utilisée pour les titres et contrôles, avec Arial/sans-serif de remplacement sur le web. La référence reste un texte sélectionnable dans un champ natif, en Consolas/monospace dans le navigateur. Aucun téléchargement de police.

## Layout

Le bandeau blanc de 100px possède trois colonnes équilibrées : Référence à gauche, signature centrée « Etude Maitre Souad CHABAB » et « By Hatim DALIL » en dessous, version à droite. La signature adopte Georgia en 24px/400, une signature secondaire de 10px avec espacement de lettres, et deux traits fins issus de la couleur de bordure existante. Cette exception typographique évoque l'en-tête d'une étude ; les formulaires conservent Segoe UI. Sous 960px, elle passe sur une seconde ligne centrée en 22px pour éviter tout chevauchement. Aucun téléchargement de police ni nouvelle couleur.

Le bureau conserve sa grille redimensionnable, marges de 24 pixels et fenêtre minimale de 660 × 640 pixels. Le web utilise une colonne de dossiers de 302 pixels et une colonne de travail fluide, largeur maximale de 1440 pixels. Sous 700 pixels, les colonnes se suivent dans le défilement naturel de la page. Seul le tableau possède un défilement interne, avec pagination serveur de 25 résultats. Aucune hauteur de viewport imposée au formulaire.

## Elevation & Depth

Pas d'ombres artificielles : bordures des contrôles Tk et bordures CSS discrètes, sans élévation décorative.

## Shapes

Contrôles rectangulaires natifs sur le bureau. Sur le web, panneaux de rayon 10 pixels et boutons/champs de rayon 6 pixels, sans popup personnalisé.

## Components

La version web 3 utilise Angular 21 standalone, FormsModule et détection zoneless. `AppComponent` possède le parcours et l'état éphémère, `ApiService` les échanges JSON et téléchargements, `FolderFieldComponent` les champs de chemin répétés et `IconComponent` la bibliothèque d'icônes SVG locale. Les templates Angular remplacent l'ancien rendu DOM manuel ; aucune seconde interface statique n'est maintenue. Les styles sont globaux pour respecter la CSP `style-src self`, sans style inline de composant. La compilation désactive l'inlining du CSS critique.

`Application._button` possède les actions, `_message` le statut persistant, `_work` le blocage des doubles soumissions. `ttk.Entry` possède les champs, `ttk.Treeview` la sélection simple, `filedialog.askdirectory` le choix de dossier natif Windows. Le système possède la géométrie des dialogues et des barres de défilement. Pas d'équivalent existant : dépôt initialement vide.

Le web réutilise `core.py` pour les règles de fichiers. Les propriétaires des formulaires, cases à cocher, statuts, pagination et téléchargements sont documentés dans `UX-CONTRACT.md`. Les styles globaux de défilement appartiennent à `frontend/src/styles.css` avec tokens thumb/track/hover/active, fallback WebKit et forced-colors. Les squelettes de chargement pulsent doucement ; reduced-motion supprime animations et transitions.

La sélection web utilise désormais des cases à cocher natives, avec compteur global et sélection de la page. `batch-dialog` reprend le rayon des panneaux, les boutons et les couleurs existants ; son contenu défile naturellement dans une hauteur maximale de 85vh. Le bilan du lot utilise des blocs de résultats avec les mêmes chemins et boutons de téléchargement, sans nouvelle palette.

La recherche directe est désormais prioritaire, avec un titre fonctionnel de 30px sur une ligne et une mise en page compacte. Le panneau de saisie libre est un `details` fermé par défaut, accessible juste après le champ de recherche, de couleur soft et de rayon de contrôle. Son textarea natif garde une hauteur suffisante et son défilement système ; la proposition modifiable utilise le même champ texte que la recherche. La mention de traitement local et l'étape de vérification font partie du contenu permanent, sans habillage de chat ou promesse d'IA générative. Après utilisation de la proposition, le panneau se replie et la recherche reprend le focus.

Un compteur de sélection est placé près des cases de la page, avec une pastille primaire lorsque la sélection est non vide. Les noms de fichiers utilisent un corps de 12px et leurs emplacements un corps secondaire de 10px ; les textes de travail sont alignés à gauche. Le trait intérieur de la ligne cochée renforce la sélection sans communiquer par la couleur seule. La progression native du lot mesure le nombre de documents traités, succès et erreurs compris, et conserve le bilan explicite par fichier. La hauteur naturelle des formulaires et le défilement propre au tableau restent indépendants.

## Do's and Don'ts

Conserver les champs après une erreur, afficher les chemins exportés après réussite, désactiver les actions pendant une opération. Ne jamais écraser une sortie ni modifier un original. La recherche est explicite et locale ; aucune référence ni aucun chemin n'est stocké dans une URL ou envoyé sur le réseau. Tester l'accessibilité avec les outils Windows avant diffusion ; aucune conformité lecteur d'écran n'est revendiquée par inspection du code.

## Édition professionnelle 3

Le rythme des nouvelles primitives utilise les tokens CSS --space-1/2/3/4/6/8 (4/8/12/16/24/32px). Le thème sombre conserve la hiérarchie et les statuts avec des surfaces bleu ardoise. Les boutons primaires utilisent --on-primary pour préserver le contraste dans les deux thèmes. La signature centrale reste le seul accent éditorial.

Décisions durables : colonne dossiers repliable (112px contre 302px), choix de thème mémorisé, tableau avec cases épinglées et en-têtes triables, parcours de confirmation en deux étapes. La page garde son défilement naturel. Les squelettes recouvrent la zone des résultats pendant le chargement sans déplacer les contrôles ; les conversions conservent leur progression réelle. Les toasts utilisent la surface et la bordure de succès existantes.

Réconciliation : ancien thème clair unique et spinner remplacés à la demande de l'utilisateur ; couleurs claires, signature, protections métier et composants de dossiers conservés. Les tokens, adaptateurs et exemples sont documentés dans GUIDE-UI.md.
