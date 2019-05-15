import { Component, Input } from '@angular/core';
import { Model } from '../data-types';

@Component({
  selector: 'timeline-cred',
  templateUrl: '../../themes/_active/cred/timeline-cred.component.html',
})
export class TimelineCredComponent {
  protected _cred: Model.Credential;

  constructor() { }

  get credential() {
    return this._cred;
  }

  @Input() set credential(cred: Model.Credential) {
    this._cred = cred;
  }

  get related_topic_name() {
    let topic = this._cred && this._cred.related_topics && this._cred.related_topics[0];
    if(topic && topic.names && topic.names.length) return topic.names[0].text;
  }

  get topic_name() {
    return this._cred && this._cred.names.length && this._cred.names[0].text;
  }

}
