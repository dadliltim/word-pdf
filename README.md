# Référence — Word vers PDF

Application interne pour Windows, en version bureau ou web locale. Recherche un document `.doc` ou `.docx` par référence ou par mots du nom, en copie le contenu sous un nom court, puis produit un PDF dans un autre dossier. Les originaux restent inchangés. Aucun document n'est envoyé à un service en ligne.

## Version web

Après avoir installé les prérequis ci-dessous, double-cliquer sur **Lancer-Web.bat**. Le navigateur s'ouvre automatiquement ; garder la fenêtre du lanceur ouverte pendant l'utilisation. Le bouton **Parcourir** ouvre le sélecteur de dossiers Windows. On peut également saisir les chemins, y compris un chemin réseau accessible au compte Windows.

Le parcours reste le même : trois dossiers → recherche → documents cochés → validation du lot → copies et PDF. Les fichiers sont enregistrés dans les dossiers choisis ; les boutons de téléchargement permettent aussi de les récupérer via le navigateur. Un téléchargement peut créer une copie supplémentaire dans le dossier Téléchargements selon les réglages du navigateur.

### Recherche et conversion de plusieurs fichiers (web)

Saisir par exemple `0677-2026 ; 0680-2026 ; MANAZIL` : le point-virgule sépare les recherches (jusqu'à 20 demandes, 300 caractères au total). Les résultats sont réunis sans afficher plusieurs fois le même fichier. Les demandes sans correspondance sont indiquées.

Cocher les documents voulus ou **Sélectionner cette page**. La sélection est conservée entre les pages ; **Tout désélectionner** la vide. Les documents sans référence numéro-année restent visibles mais ne peuvent pas être cochés. Jusqu'à 100 documents par traitement. Le bouton **Valider le renommage et convertir** ouvre un récapitulatif des documents et des deux noms de sortie ; **Annuler** n'écrit rien, **Traiter N document(s)** démarre la conversion séquentielle.

Deux documents ayant la même référence produiraient le même PDF : conserver un seul de ces documents dans le lot. Une erreur sur un fichier n'empêche pas les suivants d'être traités. Le bilan présente les réussites et erreurs par document, avec un téléchargement Word/PDF pour chaque réussite. Les fichiers réussis sont décochés, les erreurs restent sélectionnées pour une reprise manuelle. Garder l'onglet et le lanceur ouverts pendant le traitement ; aucun redémarrage automatique après interruption.

La version bureau conserve le traitement d'un document à la fois ; elle bénéficie aussi de la recherche par plusieurs demandes.

Les dossiers sont préremplis dans les deux versions et restent modifiables :

- Source : `\\Srv\data`
- Copies Word : `\\srv\gen$\Actes`
- PDF : `\\srv\gen$\Actespdf`

Ces chemins réseau nécessitent que le compte Windows utilisé ait accès au partage (lecture de la source, écriture dans les deux destinations). L'application utilise les droits Windows existants, sans enregistrer de mot de passe.

Lancement manuel : `py -3 -m word_pdf.web`. Si le port est occupé : `py -3 -m word_pdf.web --port 8766`. Arrêter le serveur avec Ctrl+C dans sa fenêtre. `--no-browser` désactive l'ouverture automatique du navigateur.

Cette version web fonctionne **localement sur le PC Windows**, sans hébergement externe ni dépendance Python supplémentaire. Les dossiers sont ceux du PC exécutant Python. Le serveur écoute uniquement en boucle locale et ne fournit pas d'accès multi-utilisateur depuis le réseau ; un déploiement partagé nécessiterait une authentification, des droits d'accès et une configuration serveur spécifiques.

## Installation sur Windows

1. Installer **Python 3.10 ou ultérieur** depuis python.org, avec le lanceur `py` et le composant **Tcl/Tk** (présent dans l'installation standard).
2. Installer **Microsoft Word pour bureau**, ou **LibreOffice** depuis libreoffice.org. Avec Word, terminer son activation et son premier démarrage avant d'utiliser l'application. Word en ligne ne suffit pas.
3. Télécharger ce dépôt puis double-cliquer sur **Lancer.bat**. Aucune bibliothèque Python supplémentaire n'est nécessaire.

On peut aussi lancer `py -3 -m word_pdf` depuis le dossier du projet.

## Utilisation

1. Choisir le dossier source ; ses sous-dossiers sont également explorés.
2. Choisir deux dossiers de sortie existants et différents : **Copies Word** et **Fichiers PDF**. Les dossiers de sortie sont exclus de la recherche lorsqu'ils se trouvent sous le dossier source. Ne pas choisir le dossier source lui-même comme dossier de sortie.
3. Saisir une référence (`0680-2026`), une partie du nom (`MANAZIL`, `SAID OUFFA`), ou le nom complet, puis lancer la recherche. Chaque mot doit apparaître dans le nom ; les majuscules, accents et espaces répétés ne bloquent pas la recherche. Les tirets typographiques et les chiffres arabes sont normalisés.
4. Sélectionner le document souhaité et vérifier les noms de sortie proposés dans la version web. Ils sont extraits du fichier sélectionné, indépendamment des mots saisis.
5. Cliquer sur **Valider le renommage et convertir** dans la version web, ou **Copier et convertir en PDF** dans la version bureau. La recherche seule n'écrit aucun fichier.

Un document sans référence numéro-année au début de son nom apparaît dans les résultats, mais son export est bloqué avec une explication : l'application ne peut pas deviner sa référence.

Exemple : `0680-2026 VI KLJKLD-IJLJL TF 12345-13.docx` donne :

- `Copies Word\0680-2026.docx` (copie du document, sans conversion de son format) ;
- `Fichiers PDF\0680-2026.pdf`.

La référence doit être au début du nom. `0680-2026 suite.doc` correspond ; `10680-2026.doc` et `0680-20260.doc` ne correspondent pas. Les extensions majuscules sont acceptées, les fichiers temporaires Word `~$…` sont ignorés. Un résultat par document est affiché ; aucune sélection arbitraire entre doublons.

## Garanties et limites

- Aucun écrasement : si la copie Word ou le PDF existe déjà, l'opération est refusée. Choisir d'autres dossiers ou déplacer soi-même les exports existants pour recommencer.
- La conversion s'effectue d'abord dans un dossier temporaire. Une erreur de conversion ne laisse pas d'export final. Si l'écriture du PDF échoue, la nouvelle copie Word est retirée. Une interruption brutale du PC peut néanmoins laisser un export incomplet.
- Les macros sont désactivées pour la conversion avec Word. Le document est ouvert en lecture seule ; les documents protégés par mot de passe ne sont pas pris en charge. Utiliser uniquement des documents internes de confiance.
- LibreOffice est utilisé si Word n'est pas disponible. La mise en page peut différer de celle de Word, notamment si les polices d'origine ne sont pas installées. Contrôler les PDF destinés à être diffusés.
- La conversion a une limite de deux minutes. En cas de blocage Word, vérifier les fenêtres Word et fermer uniquement l'instance bloquée avant de réessayer.
- Application locale sur le poste de l'utilisateur ; la variante web démarre un serveur local sans compte utilisateur ni accès distant.

## Développement et vérification

```text
python -m unittest discover -s tests -v
python -m compileall -q word_pdf
python -m word_pdf
python -m word_pdf.web --no-browser
```

Les tests automatisés vérifient la recherche, les collisions, la conservation des originaux et les erreurs d'export, avec un convertisseur de test. Ils ne prouvent pas la conversion réelle par Word. Avant diffusion sur Windows, essayer un vrai `.doc` et un vrai `.docx`, vérifier les PDF, les accents, les chemins réseau et le parcours au clavier. Le cloud Linux sans affichage ni Word ne permet pas cette validation Windows.

Les tests HTTP de `tests/test_web.py` couvrent aussi les contrôles d'accès locaux, la pagination, les exports et les téléchargements. Pour le test navigateur facultatif, installer Playwright et son Chromium dans l'environnement de développement, puis exécuter `python tests/browser_check.py`. Un Chromium existant peut être indiqué avec `CHROMIUM_EXECUTABLE`. Ce test utilise un convertisseur simulé et vérifie le parcours web, les erreurs, le clavier et une largeur de 390 pixels ; il ne valide pas Word ni le sélecteur Windows.
