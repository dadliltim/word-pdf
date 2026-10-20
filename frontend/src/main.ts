import { bootstrapApplication } from '@angular/platform-browser';
import { provideZonelessChangeDetection } from '@angular/core';
import { AppComponent } from './app/app.component';
import { registerLocaleData } from '@angular/common';
import localeFr from '@angular/common/locales/fr';

registerLocaleData(localeFr);

bootstrapApplication(AppComponent, {providers: [provideZonelessChangeDetection()]})
  .catch(() => { document.body.textContent = 'Impossible de charger Référence. Relancez Lancer-Web.bat, puis rechargez cette page.'; });
