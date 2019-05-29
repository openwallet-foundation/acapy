import { Component, Input } from '@angular/core';
import { Model } from '../data-types';

@Component({
  selector: 'topic-list',
  templateUrl: '../../themes/_active/topic/list.component.html',
  styleUrls: [
    '../../themes/_active/cred/cred.scss',
    '../../themes/_active/topic/list.component.scss']
})
export class TopicListComponent {

  @Input() public records: Model.TopicRelationship[];
  protected _format = 'rows';

  @Input() set format(fmt: string) {
    this._format = fmt;
  }

  get format(): string {
    return this._format;
  }

  typeLabel(val: string): string {
    if(val) return ('name.'+val).replace(/_/g, '-');
    return '';
  }

}
