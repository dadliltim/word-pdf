import { Component, Input } from '@angular/core';

@Component({selector: 'r-icon', standalone: true, template: '<svg aria-hidden="true" viewBox="0 0 24 24"><use [attr.href]="\'/icons.svg#\' + name" /></svg>'})
export class IconComponent { @Input() name = 'document'; }
