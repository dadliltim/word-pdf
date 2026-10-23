import { Component, ElementRef, HostListener, ViewChild, inject, signal, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DecimalPipe } from '@angular/common';
import { ApiService, DocumentItem, Exported, Proposal, SearchResult } from './api.service';
import { FolderFieldComponent } from './folder-field.component';
import { IconComponent } from './icon.component';

import { PreferencesService } from './preferences.service';
import { ToastComponent, ToastService } from './toast.component';

type FieldKey = 'source' | 'documents' | 'pdf' | 'reference';
type Tone = '' | 'error' | 'success';
interface OutputRecord {name: string; result?: Exported; error?: string;}

@Component({selector: 'app-root', standalone: true,
  imports: [FormsModule, DecimalPipe, FolderFieldComponent, IconComponent, ToastComponent], templateUrl: './app.component.html'})
export class AppComponent {
  private readonly changeDetector = inject(ChangeDetectorRef);
  readonly preferences = inject(PreferencesService);
  readonly toast = inject(ToastService);
  gridFilter = ''; sort = 'name'; descending = false; batchStep = 1;
  private filterTimer?: ReturnType<typeof setTimeout>;
  private gridRequest = 0;
  readonly loadingRows = signal(false);
  readonly api = inject(ApiService);
  readonly busy = signal(false);
  readonly notice = signal({text: 'Vos dossiers sont prêts à être utilisés. Lancez une recherche.', tone: '' as Tone});
  fields: Record<FieldKey, string> = {source: String.raw`\\Srv\data`, documents: String.raw`\\srv\gen$\Actes`, pdf: String.raw`\\srv\gen$\Actespdf`, reference: ''};
  errors: Partial<Record<FieldKey, string>> = {};
  result: SearchResult | null = null;
  selected = new Map<number, DocumentItem>();
  completed = new Set<number>();
  freeText = ''; proposal = ''; proposalVisible = false; assistantWarning = ''; assistantError = '';
  outputs: OutputRecord[] = [];
  batchItems: DocumentItem[] = []; progress = 0; progressTotal = 0;
  @ViewChild('batchDialog') dialog?: ElementRef<HTMLDialogElement>;
  @ViewChild('assistant') assistant?: ElementRef<HTMLDetailsElement>;

  get items() { return this.result?.items || []; }
  get eligible() { return this.items.filter(item => item.reference && !this.completed.has(item.index)); }
  get pageChecked() { return this.eligible.length > 0 && this.eligible.every(item => this.selected.has(item.index)); }
  get pagePartial() { return !this.pageChecked && this.eligible.some(item => this.selected.has(item.index)); }
  get canNext() { return !!this.result && (this.result.page + 1) * this.result.page_size < this.result.total; }
  get range() {
    if (!this.result?.total) return 'Aucun document';
    const start = this.result.page * this.result.page_size;
    return `${start + 1}–${Math.min(start + this.result.page_size, this.result.total)} sur ${this.result.total.toLocaleString('fr-FR')}`;
  }
  get successCount() { return this.outputs.filter(output => output.result).length; }
  get errorCount() { return this.outputs.filter(output => output.error).length; }

  note(text: string, tone: Tone = '') { this.notice.set({text, tone}); if (tone === 'success') this.toast.show(text); }
  message(error: unknown) { return error instanceof Error ? error.message : 'Une erreur inattendue est survenue. Réessayez.'; }
  focus(id: string) { queueMicrotask(() => document.getElementById(id)?.focus()); }
  edit(key: FieldKey, value: string) {
    this.fields[key] = value; delete this.errors[key]; this.reset();
    this.note('Paramètres modifiés. Lancez une recherche pour continuer.');
  }
  reset() {
    this.gridRequest++; clearTimeout(this.filterTimer); this.gridFilter = ''; this.sort = 'name'; this.descending = false; this.loadingRows.set(false);
    this.result = null; this.selected.clear(); this.completed.clear(); this.outputs = [];
    this.progress = 0; this.progressTotal = 0;
  }
  clear() { this.edit('reference', ''); this.focus('reference'); }
  guardComposition(event: Event) { if ((event as KeyboardEvent).isComposing) event.preventDefault(); }

  async search() {
    if (this.busy()) return;
    this.errors = {};
    for (const key of Object.keys(this.fields) as FieldKey[]) {
      if (!this.fields[key].trim()) this.errors[key] = key === 'reference' ? 'Saisissez un nom, un mot ou une référence.' : 'Choisissez un dossier existant.';
    }
    if (this.fields.reference.length > 300) this.errors.reference = 'Limitez la recherche à 300 caractères.';
    const invalid = Object.keys(this.errors)[0];
    if (invalid) { this.focus(invalid); this.note('Complétez les champs indiqués avant de rechercher.', 'error'); return; }
    this.reset(); this.loadingRows.set(true); this.busy.set(true); this.note('Recherche dans le dossier source et ses sous-dossiers…');
    try {
      this.result = await this.api.post<SearchResult>('search', this.fields);
      this.note(this.result.total ? `${this.result.total} document(s) trouvé(s). Cochez ceux à convertir.` : 'Aucun document trouvé. Essayez un autre nom ou une autre référence.');
    } catch (error) { this.note(this.message(error), 'error'); }
    finally { this.busy.set(false); this.loadingRows.set(false); }
  }

  async browse(key: FieldKey) {
    if (this.busy()) return;
    this.busy.set(true); this.note('Choisissez un dossier dans la fenêtre de sélection du PC.');
    try {
      const result = await this.api.post<{path: string}>('browse', {});
      if (result.path) this.edit(key, result.path); else this.note('Sélection annulée. Vos dossiers sont conservés.');
    } catch (error) { this.note(this.message(error), 'error'); }
    finally { this.busy.set(false); }
  }

  editFreeText(value: string) {
    this.freeText = value; this.proposal = ''; this.proposalVisible = false; this.assistantError = '';
  }
  async prepare() {
    if (this.busy()) return;
    this.assistantError = ''; this.proposalVisible = false; this.proposal = '';
    if (!this.freeText.trim() || this.freeText.length > 2000) {
      this.assistantError = 'Décrivez votre recherche en 2 000 caractères maximum.'; this.focus('free-request'); return;
    }
    this.busy.set(true); this.note('Préparation locale des recherches…');
    try {
      const result = await this.api.post<Proposal>('prepare-search', {text: this.freeText});
      this.proposal = result.queries.join(' ; '); this.proposalVisible = true;
      this.assistantWarning = result.warnings.join('\n') || 'Vérifiez les références et les noms avant de les utiliser.';
      this.note(result.queries.length ? 'Recherches proposées. Vérifiez-les avant de les utiliser.' : 'Précisez votre demande ou utilisez la recherche directe.');
    } catch (error) { this.assistantError = this.message(error); this.note(this.assistantError, 'error'); }
    finally { this.busy.set(false); }
  }
  useProposal() {
    if (this.busy() || !this.proposal.trim()) return;
    this.edit('reference', this.proposal.trim());
    if (this.assistant) this.assistant.nativeElement.open = false;
    this.focus('reference'); this.note('Recherches prêtes. Cliquez sur Rechercher pour consulter les documents.');
  }

  toggle(item: DocumentItem, event: Event) {
    if (this.busy() || !item.reference || this.completed.has(item.index)) return;
    if ((event.target as HTMLInputElement).checked) this.selected.set(item.index, item); else this.selected.delete(item.index);
  }
  togglePage(event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    for (const item of this.eligible) { if (checked) this.selected.set(item.index, item); else this.selected.delete(item.index); }
  }
  deselect() { this.selected.clear(); }
  async page(direction: number) {
    if (this.busy() || !this.result) return;
    await this.loadGrid(this.result.page + direction);
  }
  filterGrid(value: string, composing = false) {
    this.gridFilter = value; clearTimeout(this.filterTimer); this.gridRequest++;
    if (!composing) this.filterTimer = setTimeout(() => void this.loadGrid(0), 300);
  }
  clearFilter() { this.gridFilter = ''; clearTimeout(this.filterTimer); void this.loadGrid(0); this.focus('grid-filter'); }
  sortGrid(key: string) {
    if (this.sort === key) this.descending = !this.descending;
    else { this.sort = key; this.descending = false; }
    void this.loadGrid(0);
  }
  async loadGrid(page: number) {
    if (!this.result || this.busy()) return;
    const request = ++this.gridRequest, searchId = this.result.search_id;
    this.loadingRows.set(true);
    try {
      const result = await this.api.post<SearchResult>('page', {search_id: searchId, page, filter: this.gridFilter, sort: this.sort, descending: this.descending});
      if (request !== this.gridRequest) return;
      this.result = result; this.note('Résultats actualisés. Votre sélection est conservée.');
    } catch (error) { if (request === this.gridRequest) this.note(this.message(error), 'error'); }
    finally { if (request === this.gridRequest) this.loadingRows.set(false); }
  }
  @HostListener('document:keydown', ['$event']) shortcuts(event: KeyboardEvent) {
    if (event.isComposing || this.dialog?.nativeElement.open) return;
    if (event.ctrlKey && !event.shiftKey && event.key.toLowerCase() === 'k') { event.preventDefault(); this.focus('reference'); }
    if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'l') { event.preventDefault(); this.preferences.toggleTheme(); }
    if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'b') { event.preventDefault(); this.preferences.toggleSidebar(); }
  }

  confirmSelection() {
    if (this.busy() || !this.result || !this.selected.size) return;
    const items = [...this.selected.values()], references = new Set<string>();
    if (items.length > 100) { this.note('Traitez au maximum 100 documents à la fois.', 'error'); return; }
    for (const item of items) {
      if (!item.reference || references.has(item.reference)) {
        this.note(`Plusieurs documents produiraient ${item.reference}.pdf. Gardez un seul document pour cette référence.`, 'error'); return;
      }
      references.add(item.reference);
    }
    this.batchStep = 1; this.batchItems = items; this.changeDetector.detectChanges(); this.dialog?.nativeElement.showModal(); document.getElementById('cancel-batch')?.focus();
  }
  closeDialog() { this.dialog?.nativeElement.close(); }
  nextStep() { this.batchStep = 2; this.focus('cancel-batch'); }
  previousStep() { this.batchStep = 1; this.focus('cancel-batch'); }
  trapFocus(event: KeyboardEvent) {
    if (event.key !== 'Tab') return;
    const buttons = this.dialog?.nativeElement.querySelectorAll<HTMLButtonElement>('button:not([disabled])');
    if (!buttons?.length) return;
    const visible = Array.from(buttons).filter(button => button.getClientRects().length > 0);
    const first = visible[0], last = visible[visible.length - 1];
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
  async exportBatch() {
    if (this.batchStep !== 2 || this.busy() || !this.result || !this.batchItems.length) return;
    const items = [...this.batchItems], searchId = this.result.search_id;
    this.closeDialog(); this.busy.set(true); this.outputs = []; this.progress = 0; this.progressTotal = items.length;
    for (const [position, item] of items.entries()) {
      this.note(`Traitement ${position + 1}/${items.length} : ${item.name}. Jusqu’à deux minutes par document.`);
      try {
        const output = await this.api.post<Exported>('export', {search_id: searchId, index: item.index});
        this.outputs = [...this.outputs, {name: item.name, result: output}];
        this.selected.delete(item.index); this.completed.add(item.index);
      } catch (error) { this.outputs = [...this.outputs, {name: item.name, error: this.message(error)}]; }
      this.progress = position + 1;
      this.note(`Traitement ${this.progress}/${items.length} : ${this.successCount} réussi(s), ${this.errorCount} échec(s).`);
    }
    this.note(`Traitement terminé : ${this.successCount} réussi(s), ${this.errorCount} échec(s). Les documents en échec restent cochés.`, this.errorCount ? 'error' : 'success');
    this.busy.set(false);
  }
  async download(output: Exported, kind: 'word' | 'pdf') {
    if (this.busy()) return;
    this.busy.set(true);
    try { await this.api.download(output, kind); this.note('Téléchargement demandé. Le fichier reste également dans son dossier de sortie.', 'success'); }
    catch (error) { this.note(this.message(error), 'error'); }
    finally { this.busy.set(false); }
  }
  @HostListener('window:beforeunload', ['$event']) beforeUnload(event: BeforeUnloadEvent) {
    if (this.busy()) { event.preventDefault(); event.returnValue = ''; }
  }
}
