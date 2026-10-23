import { Injectable, signal } from '@angular/core';
@Injectable({providedIn: 'root'})
export class PreferencesService {
  readonly dark = signal(document.documentElement.dataset['theme'] === 'dark');
  readonly collapsed = signal(this.read('reference-sidebar') === 'collapsed');
  private read(key: string) { try { return localStorage.getItem(key); } catch { return null; } }
  private save(key: string, value: string) { try { localStorage.setItem(key, value); } catch { /* Préférence facultative. */ } }
  toggleTheme() { this.dark.update(value => !value); const theme = this.dark() ? 'dark' : 'light'; document.documentElement.dataset['theme'] = theme; this.save('reference-theme', theme); }
  toggleSidebar() { this.collapsed.update(value => !value); this.save('reference-sidebar', this.collapsed() ? 'collapsed' : 'expanded'); }
}
