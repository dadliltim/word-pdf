import { Component, ElementRef, HostListener, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DecimalPipe } from '@angular/common';
import { ApiService, DocumentItem, Exported, Proposal, SearchResult } from './api.service';
import { FolderFieldComponent } from './folder-field.component';
import { IconComponent } from './icon.component';

type FieldKey = 'source' | 'documents' | 'pdf' | 'reference';
type Tone = '' | 'error' | 'success';
interface OutputRecord {name: string; result?: Exported; error?: string;}

@Component({selector: 'app-root', standalone: true,
  imports: [FormsModule, DecimalPipe, FolderFieldComponent, IconComponent], templateUrl: './app.component.html'})
export class AppComponent {
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

  note(text: string, tone: Tone = '') { this.notice.set({text, tone}); }
  message(error: unknown) { return error instanceof Error ? error.message : 'Une erreur inattendue est survenue. Réessayez.'; }
  focus(id: string) { queueMicrotask(() => document.getElementById(id)?.focus()); }
  edit(key: FieldKey, value: string) {
    this.fields[key] = value; delete this.errors[key]; this.reset();
    this.note('Paramètres modifiés. Lancez une recherche pour continuer.');
  }
  reset() {
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
    this.reset(); this.busy.set(true); this.note('Recherche dans le dossier source et ses sous-dossiers…');
    try {
      this.result = await this.api.post<SearchResult>('search', this.fields);
      this.note(this.result.total ? `${this.result.total} document(s) trouvé(s). Cochez ceux à convertir.` : 'Aucun document trouvé. Essayez un autre nom ou une autre référence.');
    } catch (error) { this.note(this.message(error), 'error'); }
    finally { this.busy.set(false); }
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
    this.busy.set(true); this.note('Chargement des documents…');
    try {
      this.result = await this.api.post<SearchResult>('page', {search_id: this.result.search_id, page: this.result.page + direction});
      this.note('Votre sélection est conservée entre les pages.');
    } catch (error) { this.note(this.message(error), 'error'); }
    finally { this.busy.set(false); }
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
    this.batchItems = items; this.dialog?.nativeElement.showModal(); this.focus('cancel-batch');
  }
  closeDialog() { this.dialog?.nativeElement.close(); }
  trapFocus(event: KeyboardEvent) {
    if (event.key !== 'Tab') return;
    if (event.shiftKey && document.activeElement?.id === 'cancel-batch') { event.preventDefault(); this.focus('confirm-batch'); }
    else if (!event.shiftKey && document.activeElement?.id === 'confirm-batch') { event.preventDefault(); this.focus('cancel-batch'); }
  }
  async exportBatch() {
    if (this.busy() || !this.result || !this.batchItems.length) return;
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
