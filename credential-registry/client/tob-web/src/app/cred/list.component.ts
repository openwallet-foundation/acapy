import { Component, Input } from '@angular/core';
import { Model } from '../data-types';

@Component({
  selector: 'cred-list',
  templateUrl: '../../themes/_active/cred/list.component.html',
  styleUrls: [
    '../../themes/_active/cred/cred.scss',
    '../../themes/_active/cred/list.component.scss']
})
export class CredListComponent {

  @Input() records: Model.Credential[];
  protected _format = 'cards';

  @Input() set format(fmt: string) {
    this._format = fmt;
  }

  get format(): string {
    return this._format;
  }

}
