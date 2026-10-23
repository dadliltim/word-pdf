# Référence — édition professionnelle 3

Cette variante Angular conserve le moteur Python de recherche et de conversion Windows. Le dépôt ne contient pas de backend Express. Le navigateur reste local, les originaux sont conservés et aucune sortie existante n'est écrasée.

## Design system

L'interface évoque un dossier d'étude : en-tête signé, référence lisible, dossiers visibles et vérification avant traitement. Aucune statistique fictive n'est ajoutée.

| Rôle | Clair | Sombre |
|---|---|---|
| Fond | `#EAF0F5` | `#101B28` |
| Surface | `#FFFFFF` | `#192838` |
| Texte | `#19334A` | `#E5EDF5` |
| Action | `#155D83` | `#93C8EB` |
| Texte secondaire | `#506477` | `#B1C0CE` |
| Erreur | `#A12431` | `#FFB0B7` |

Les six couleurs claires appartiennent à `word_pdf/theme.json` et sont servies par `/theme.css`. Les couleurs sombres, les rôles auxiliaires et les espacements appartiennent à `frontend/src/styles.css`. Éviter des valeurs de couleur indépendantes dans les composants.

```css
/* Exemple réutilisable avec les tokens réellement disponibles. */
.contract-field {
  padding: var(--space-3) var(--space-4);
  color: var(--ink);
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 6px;
}
.contract-field:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 3px;
}
```

Échelle 4, 8, 12, 16, 24, 32 px. Segoe UI/system-ui pour travailler sans téléchargement de police ; Consolas pour les références ; Georgia uniquement pour la signature centrale de l'étude. Titres 30/21/17 px, corps et contrôles 12–14 px. Les informations secondaires denses restent zoomables. Les champs gardent leur label visible. Les statuts comportent toujours un texte explicite.

Le thème suit le système au premier lancement puis mémorise le choix manuel. Le script local `theme-init.js` applique le thème avant l'affichage Angular. Seuls le thème et le repli des dossiers sont conservés dans localStorage, jamais les noms, chemins ou recherches.

## Interactions livrées

- Dossiers repliables et mémorisés ; raccourci Ctrl+Maj+B.
- Recherche : Ctrl+K. Thème : Ctrl+Maj+L. Les raccourcis sont ignorés pendant une composition IME et dans le dialogue modal.
- Squelettes pendant le chargement des résultats ; progression réelle par document pendant la conversion. Aucune progression de conversion fictive.
- Toast de réussite dédupliqué, fermable et annoncé, pendant six secondes ; le bilan persistant contient toujours l'information complète. Les erreurs restent dans le statut et les champs concernés.
- Transitions de survol de 150 ms et retour pressé de 1 px. `prefers-reduced-motion` désactive animations et transitions.

Les propriétaires réutilisables sont `PreferencesService`, `ToastService`, `ToastComponent`, `FolderFieldComponent`, `IconComponent` et `ApiService`. Exemple d'utilisation dans un futur composant :

```ts
import { Component, inject } from '@angular/core';
import { ToastService } from './toast.component';

@Component({
  selector: 'app-save-notice', standalone: true,
  template: `<button type="button" (click)="acknowledge()">Confirmer la vérification</button>`
})
export class SaveNoticeComponent {
  private readonly toast = inject(ToastService);
  acknowledge() { this.toast.show('Vérification confirmée.'); }
}
```

Pour une sauvegarde réelle, appeler le toast uniquement après la réponse positive du serveur. Ne jamais présenter une réussite optimiste pour une conversion ou une écriture de fichier.

## Tableau dense

Table HTML sémantique, 25 résultats par page, en-têtes fixes et colonne des cases épinglée. Les boutons d'en-tête exposent `aria-sort`. Le tri nom/format et le filtre portent sur **tous** les résultats mémorisés par le serveur, sans relire le disque à chaque frappe. Le filtre est différé de 300 ms, respecte l'IME et ignore les réponses obsolètes. Un effacement recharge immédiatement. Les index restent stables pour éviter de traiter le mauvais fichier après tri.

```ts
// Contrat utilisé par AppComponent.loadGrid :
const result = await api.post<SearchResult>('page', {
  search_id: searchId,
  page: 0,
  filter: 'MANAZIL',
  sort: 'name',
  descending: false
});
```

La sélection couvre plusieurs pages et reste conservée lors du filtrage ; le compteur indique cette portée. Une modification de la recherche ou des dossiers invalide la sélection. Aucun chemin ne figure dans une URL partageable. Sur mobile, seul le tableau défile horizontalement.

## Parcours multi-étapes

Le parcours réel d'export comporte deux étapes : vérifier les documents et les noms proposés, puis confirmer les destinations. Retour et Annuler n'écrivent rien. Seul le bouton final lance la conversion. Les doublons de référence et les lots de plus de 100 documents sont refusés avant ouverture. Les destinations restent en lecture seule dans le dialogue pour correspondre exactement à la recherche validée côté serveur.

Pour un futur formulaire de création d'acte, utiliser les Reactive Forms et valider chaque groupe avant de passer à la suite. Ce modèle est un exemple d'extension, pas un nouvel éditeur d'actes livré :

```ts
import { FormControl, FormGroup, Validators } from '@angular/forms';

readonly identification = new FormGroup({
  reference: new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.pattern(/^\d{4}-\d{4}$/)]
  })
});
step = 1;
next() {
  this.identification.markAllAsTouched();
  if (this.identification.invalid) return; // Focaliser le premier invalide dans la vue.
  this.step = 2;
}
```

```html
<!-- Dans un composant important ReactiveFormsModule. -->
<form [formGroup]="identification" novalidate>
  <label for="act-reference">Référence (obligatoire)</label>
  <input id="act-reference" formControlName="reference"
    aria-describedby="act-reference-help act-reference-error"
    [attr.aria-invalid]="identification.controls.reference.touched && identification.controls.reference.invalid">
  <p id="act-reference-help">Format attendu : 0680-2026.</p>
  <p id="act-reference-error">
    @if (identification.controls.reference.touched && identification.controls.reference.invalid) {
      Saisissez quatre chiffres, un tiret et l’année sur quatre chiffres.
    }
  </p>
</form>
```

Pour les références de fichiers, conserver le parseur serveur existant, plus souple que cette validation illustrative. Ne pas réimplémenter ses règles de normalisation arabe côté navigateur. Pour un vrai éditeur juridique, définir les champs, permissions et transitions métier avant de créer le formulaire.

## Organisation Angular recommandée

```text
app/
  api.service.ts              # Adaptateur HTTP et erreurs réseau
  preferences.service.ts      # Préférences non sensibles
  toast.component.ts          # Service + présentation des notifications
  folder-field.component.ts   # Composant de présentation : inputs/outputs
  icon.component.ts           # Icônes locales
  app.component.ts            # Orchestration actuelle du parcours
  app.component.html          # Vue de recherche et traitement
```

Pour ajouter plusieurs écrans, déplacer l'orchestration vers `features/documents/`, placer les composants communs dans `shared/ui/` et les services dans `core/`. Introduire le routeur lorsqu'il existe de vraies destinations. Les composants de présentation reçoivent leurs données par input et remontent une intention par output ; les services possèdent le réseau et les préférences. Éviter de créer un store global pour un seul écran.

| Bibliothèque | À privilégier quand | Vigilance |
|---|---|---|
| Angular Material + CDK | Nombreux formulaires, dialogues, menus et steppers | Personnaliser les tokens ; vérifier le français et le focus |
| PrimeNG | ERP avec grilles complexes, colonnes multiples, édition | Taille du bundle, licence/version, comportement de sélection |
| Tailwind CSS | Équipe qui veut composer son propre système visuel | Ne fournit ni focus trap ni composants accessibles à lui seul |

Cette version garde les composants natifs et Angular standalone existants : une seule surface, sans nouvelle dépendance UI. Si le produit devient un ERP, privilégier Material/CDK pour les formulaires ou PrimeNG pour les grilles ; éviter de mélanger deux bibliothèques complètes.

## Backend et validation

Un futur backend Express peut reprendre les contrats JSON search/page/export via un adaptateur, mais doit préserver les protections : chemins autorisés, jeton/session, contrôle d'origine, index serveur stable, refus d'écrasement, conversion séquentielle et bilan par fichier. Une migration Express nécessite une tâche distincte ; elle n'est pas simulée ici.

Vérification : typecheck TypeScript, build Angular, tests Python, parcours Chromium et audit axe automatisé sur les états couverts. Cible WCAG 2.2 AA ; ces contrôles ne constituent pas une certification. La conversion réelle Microsoft Word et le choix natif des dossiers restent à vérifier sur Windows.
