import { Injectable } from '@angular/core';

export interface DocumentItem {
  index: number; name: string; folder: string; reference: string | null;
  reference_error: string | null; extension: string;
}
export interface SearchResult {
  search_id: string; reference: string; page: number; total: number;
  page_size: number; items: DocumentItem[]; missing_queries: string[];
}
export interface Exported { export_id: string; word: string; pdf: string; }
export interface Proposal {queries: string[]; warnings: string[]; mode: string;}

@Injectable({providedIn: 'root'})
export class ApiService {
  readonly version = document.querySelector<HTMLMetaElement>('meta[name="app-version"]')?.content || '';
  private readonly token = document.querySelector<HTMLMetaElement>('meta[name="app-token"]')?.content || '';

  async post<T>(route: string, body: unknown, binary = false): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`/api/${route}`, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-App-Token': this.token}, body: JSON.stringify(body)});
    } catch {
      throw new Error(route === 'export'
        ? 'Connexion interrompue. La conversion a peut-être abouti : vérifiez les dossiers de sortie avant de réessayer.'
        : 'Le serveur ne répond pas. Gardez la fenêtre Lancer-Web ouverte, puis réessayez.');
    }
    if (!response.ok) {
      let message = 'L’opération n’a pas pu être effectuée. Réessayez.';
      try { const error = await response.json(); message = error.error || message; } catch { /* Réponse non JSON. */ }
      throw new Error(message);
    }
    return (binary ? response.blob() : response.json()) as Promise<T>;
  }

  async download(output: Exported, kind: 'word' | 'pdf') {
    const blob = await this.post<Blob>('download', {export_id: output.export_id, kind}, true);
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = output[kind].split(/[\\/]/).pop() || 'document';
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
}
