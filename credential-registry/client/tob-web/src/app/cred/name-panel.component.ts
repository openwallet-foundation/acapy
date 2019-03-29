import { Component, Input } from '@angular/core';
import { Model } from '../data-types';

@Component({
  selector: 'name-panel',
  templateUrl: '../../themes/_active/cred/name-panel.component.html',
  styleUrls: [
    '../../themes/_active/cred/cred.scss',
    '../../themes/_active/cred/name-panel.component.scss']
})
export class NamePanelComponent {

  @Input() record: Model.Topic;
  @Input() link: boolean = false;

  get name(): Model.Name {
    return this.record.preferredName;
  }

  get issuer(): Model.Issuer {
    return this.name ? this.name.issuer : null;
  }

}
