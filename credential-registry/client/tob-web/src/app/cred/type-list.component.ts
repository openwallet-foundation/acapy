import { Component, Input } from '@angular/core';
import { Model } from '../data-types';

@Component({
  selector: 'cred-type-list',
  templateUrl: '../../themes/_active/cred/type-list.component.html',
  styleUrls: [
    '../../themes/_active/cred/cred.scss',
    '../../themes/_active/cred/type-list.component.scss']
})
export class CredTypeListComponent {

  @Input() records: Model.CredentialType[];

}
