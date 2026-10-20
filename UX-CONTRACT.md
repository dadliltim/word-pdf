# Contrat d'interaction — Référence web

Source métier : demande utilisateur dans cette session, recherche d'une référence en début de nom, copie renommée et PDF dans deux dossiers différents ; précisions utilisateur : Windows et nom court `0680-2026`. Le dépôt était vide avant cette implémentation. Pas de facturation, suppression ou changement des permissions.

## Propriété canonique

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Form | `validate`, `updateControls` dans `static/app.js` | Ce contrat : champs natifs étiquetés, erreurs inline, premier invalide focalisé | Recherche explicite | `tests/browser_check.py` |
| Table Selection | `selected`, `render`, `updateControls` dans `static/app.js` | Ce contrat : cases natives, sélection conservée entre pages, effacée au changement de recherche | Lignes individuelles, sélection de la page, tout désélectionner | `tests/browser_check.py` |
| Scrollbar | `static/app.css` | DESIGN.md : baseline globale, standards et WebKit, forced-colors | Tableau borné et document naturel | `tests/browser_check.py` |

Autres propriétaires : `_page` dans `web.py` pour la pagination serveur de 25 et les bornes (`tests/test_web.py`) ; `/api/browse` pour le dialogue système avec saisie manuelle équivalente (validation Windows restante) ; `status` dans `static/app.js` pour la région live persistante (`tests/browser_check.py`) ; `core.export_document` pour la conservation des originaux et le refus d'écrasement (`tests/test_core.py`, `tests/test_web.py`).

## Parcours et récupération

Trois dossiers → référence → recherche explicite → choix du document → export → chemins et téléchargement. Les paramètres restent présents après une erreur. Les actions sont désactivées pendant une requête pour éviter les doubles soumissions et les réponses obsolètes. IME : Entrée pendant composition ne soumet pas la recherche. Le bouton Effacer vide immédiatement la recherche et restaure le focus. Aucune recherche automatique à chaque frappe.

Le champ accepte une référence, des mots du nom ou le nom complet et conserve la saisie. Une référence exacte recherche le préfixe avec une borne pour éviter les numéros voisins ; les autres recherches exigent que chaque mot figure dans le nom, sans distinction de casse ou d'accents. Les espaces autour du tiret, tirets typographiques et chiffres arabes/persans/pleine largeur sont normalisés ; les zéros initiaux sont conservés. Chaque résultat possède sa propre référence initiale extraite par le serveur. La sélection affiche les deux noms proposés avant le clic explicite sur « Valider le renommage et convertir ». La recherche ne copie et ne convertit rien. Un fichier sans référence est affiché, mais l'export est indisponible avec une explication, sans inventer de nom.

Les chemins et références restent en mémoire uniquement, sans URL, localStorage ou journal HTTP. Le rechargement réinitialise la page ; avertissement du navigateur uniquement si une opération est active. Le serveur garde jusqu'à 20 recherches et 100 références d'export en mémoire, puis évince les plus anciennes, sans supprimer les fichiers. Une recherche expirée doit être relancée. Une réponse réseau perdue après export peut masquer une réussite : le message demande de vérifier les dossiers avant de réessayer.

## Traitement par lot

### Préparation depuis du texte libre

`assistant.prepare_search` et `/api/prepare-search` possèdent l'interprétation locale (sans LLM). `assistant-form` possède la saisie et les erreurs inline ; `assistant-proposal` affiche une proposition modifiable. `use-proposal` copie uniquement la proposition vers le champ de recherche et lui rend le focus, sans déclencher recherche ou export. Une modification de la demande invalide immédiatement la proposition antérieure. Pendant une requête, champs et textarea sont désactivés. La demande n'est ni journalisée ni persistée. Le mode local et ses limites sont nommés dans l'interface ; aucune compréhension générale n'est promise. Vérification : `tests/test_assistant.py`, `tests/test_web.py`, `tests/browser_check.py`.

Les points-virgules séparent jusqu'à 20 recherches (300 caractères). Les résultats sont une union dédupliquée, et les demandes sans résultat sont affichées. Chaque espace entre mots reste une recherche de tous ces mots dans un même nom. Les noms complets contenant un point-virgule ne peuvent donc pas être recherchés littéralement en une seule demande ; utiliser un autre fragment du nom.

La sélection peut couvrir plusieurs pages, avec un compteur global et une case « Sélectionner cette page » à état intermédiaire. Les fichiers sans référence ou déjà réussis dans cette recherche sont désactivés. Une nouvelle recherche efface la sélection. Maximum 100 documents par lot ; les variantes produisant le même PDF sont refusées avant confirmation.

`batch-dialog` est le propriétaire canonique de la confirmation : dialogue HTML natif modal, titre et description accessibles, aperçu de tous les noms, focus initial sur Annuler, Escape annule, focus rendu au bouton de traitement. Aucun export avant le clic sur « Traiter N document(s) ». `confirm-batch` envoie une requête par fichier, séquentiellement, avec état occupé et progression réelle par compteur. Les réussites sont retirées de la sélection ; les erreurs restent cochées. Une panne de réseau peut laisser une réussite non confirmée : vérifier les dossiers avant de reprendre. Le bilan persiste jusqu'à une nouvelle recherche ou un nouveau traitement, sans stockage local.

## Limite d'accès du serveur

Application web locale mono-poste, écoute uniquement sur `127.0.0.1`. Vérification Host, Origin et jeton de démarrage sur les opérations, pas de CORS. Les téléchargements sont limités aux sorties enregistrées par le processus. Ne pas exposer ce serveur sur Internet ou le réseau interne sans une tâche distincte ajoutant authentification, autorisations et déploiement serveur. Les dossiers sont ceux du PC qui exécute Python ; un navigateur distant ne donne pas accès automatiquement à ses propres dossiers.

## Locale et accessibilité

Français (`lang=fr`), quantités formatées en `fr-FR`, aucune donnée japonaise. Contrôles HTML natifs, focus visible, région de statut accessible, palette compatible contraste texte, animations supprimées avec reduced-motion. Tableau défilant sur petit écran ; la page conserve son défilement naturel. Pas de dialogue ou select personnalisé.
