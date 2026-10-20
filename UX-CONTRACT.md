# Contrat d'interaction — Référence web

Source métier : demande utilisateur dans cette session, recherche d'une référence en début de nom, copie renommée et PDF dans deux dossiers différents ; précisions utilisateur : Windows et nom court `0680-2026`. Le dépôt était vide avant cette implémentation. Pas de facturation, suppression ou changement des permissions.

## Propriété canonique

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Form | `validate`, `updateControls` dans `static/app.js` | Ce contrat : champs natifs étiquetés, erreurs inline, premier invalide focalisé | Recherche explicite | `tests/browser_check.py` |
| Table Selection | `render` dans `static/app.js` | Ce contrat : radio natif, un document, sélection annulée au changement de page | Une ligne de la page courante | `tests/browser_check.py` |
| Scrollbar | `static/app.css` | DESIGN.md : baseline globale, standards et WebKit, forced-colors | Tableau borné et document naturel | `tests/browser_check.py` |

Autres propriétaires : `_page` dans `web.py` pour la pagination serveur de 25 et les bornes (`tests/test_web.py`) ; `/api/browse` pour le dialogue système avec saisie manuelle équivalente (validation Windows restante) ; `status` dans `static/app.js` pour la région live persistante (`tests/browser_check.py`) ; `core.export_document` pour la conservation des originaux et le refus d'écrasement (`tests/test_core.py`, `tests/test_web.py`).

## Parcours et récupération

Trois dossiers → référence → recherche explicite → choix du document → export → chemins et téléchargement. Les paramètres restent présents après une erreur. Les actions sont désactivées pendant une requête pour éviter les doubles soumissions et les réponses obsolètes. IME : Entrée pendant composition ne soumet pas la recherche. Le bouton Effacer vide immédiatement la recherche et restaure le focus. Aucune recherche automatique à chaque frappe.

Les chemins et références restent en mémoire uniquement, sans URL, localStorage ou journal HTTP. Le rechargement réinitialise la page ; avertissement du navigateur uniquement si une opération est active. Le serveur garde jusqu'à 20 recherches et 100 références d'export en mémoire, puis évince les plus anciennes, sans supprimer les fichiers. Une recherche expirée doit être relancée. Une réponse réseau perdue après export peut masquer une réussite : le message demande de vérifier les dossiers avant de réessayer.

## Limite d'accès

Application web locale mono-poste, écoute uniquement sur `127.0.0.1`. Vérification Host, Origin et jeton de démarrage sur les opérations, pas de CORS. Les téléchargements sont limités aux sorties enregistrées par le processus. Ne pas exposer ce serveur sur Internet ou le réseau interne sans une tâche distincte ajoutant authentification, autorisations et déploiement serveur. Les dossiers sont ceux du PC qui exécute Python ; un navigateur distant ne donne pas accès automatiquement à ses propres dossiers.

## Locale et accessibilité

Français (`lang=fr`), quantités formatées en `fr-FR`, aucune donnée japonaise. Contrôles HTML natifs, focus visible, région de statut accessible, palette compatible contraste texte, animations supprimées avec reduced-motion. Tableau défilant sur petit écran ; la page conserve son défilement naturel. Pas de dialogue ou select personnalisé.
