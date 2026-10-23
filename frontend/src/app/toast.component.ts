import { Component, Injectable, inject, signal } from '@angular/core';
@Injectable({providedIn: 'root'})
export class ToastService {
  readonly message = signal('');
  private timer?: ReturnType<typeof setTimeout>;
  show(message: string) { clearTimeout(this.timer); this.message.set(message); this.timer = setTimeout(() => this.dismiss(), 6000); }
  dismiss() { clearTimeout(this.timer); this.message.set(''); }
}
@Component({selector: 'r-toast', standalone: true, template: `<div class="toast-region" role="status" aria-live="polite">@if (toast.message()) {<div class="toast"><span>{{ toast.message() }}</span><button type="button" (click)="toast.dismiss()" aria-label="Fermer la notification">×</button></div>}</div>`})
export class ToastComponent { readonly toast = inject(ToastService); }
