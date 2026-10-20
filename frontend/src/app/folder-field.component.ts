import { Component, Input, Output, EventEmitter } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IconComponent } from './icon.component';

@Component({
  selector: 'r-folder-field', standalone: true, imports: [FormsModule, IconComponent],
  template: `<div class="folder-field"><div class="field-heading"><span class="folder-symbol"><r-icon [name]="icon" /></span><label [for]="fieldId">{{ label }}</label></div>
    <input [id]="fieldId" [name]="fieldId" [ngModel]="value" (ngModelChange)="valueChange.emit($event)" [disabled]="busy" autocomplete="off" spellcheck="false" [attr.aria-invalid]="!!error" [attr.aria-describedby]="fieldId + '-error'">
    <p class="field-error" [id]="fieldId + '-error'">{{ error }}</p><div class="field-bottom"><span>{{ help }}</span><button type="button" class="browse" (click)="browse.emit()" [disabled]="busy">Parcourir<r-icon name="folder-open" /></button></div></div>`
})
export class FolderFieldComponent {
  @Input() fieldId = ''; @Input() label = ''; @Input() icon = 'folder';
  @Input() value = ''; @Input() busy = false; @Input() error = ''; @Input() help = '';
  @Output() valueChange = new EventEmitter<string>(); @Output() browse = new EventEmitter<void>();
}
