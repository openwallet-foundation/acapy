import { Component, OnInit, OnDestroy, Input, ChangeDetectionStrategy } from '@angular/core';
import { GeneralDataService } from '../general-data.service';
import { Fetch, Model } from '../data-types';
import { Subscription } from 'rxjs/Subscription';
import { TimelineFormatterService } from './timeline-formatter.service';


@Component({
  selector: 'credset-timeline',
  templateUrl: '../../themes/_active/cred/timeline.component.html',
  styleUrls: ['../../themes/_active/cred/timeline.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CredSetTimelineComponent implements OnInit, OnDestroy {
  protected _topicId: number;
  private _range;
  private _rows = [];

  private _loader: Fetch.ModelListLoader<Model.CredentialSet>;

  constructor(
    private _dataService: GeneralDataService,
    private _formatter: TimelineFormatterService,
  ) {
  }

  ngOnInit() {
    this._loader = new Fetch.ModelListLoader(Model.CredentialSet);
    this._loader.stream.subscribe(this.updateRows.bind(this));
    this.load();
  }

  ngOnDestroy() {
    this._loader.complete();
  }

  get result$() {
    return this._loader.stream;
  }

  get topicId(): number {
    return this._topicId;
  }

  @Input() set topicId(newId: number) {
    this._topicId = newId;
    this.load();
  }

  get timelineRows() {
    return this._rows;
  }

  get timelineRange() {
    return this._range;
  }

  updateRows(result) {
    if(result.loaded) {
      let rows = [];
      let start = new Date();
      start.setFullYear(start.getFullYear() - 1);
      let end = new Date();
      end.setFullYear(end.getFullYear() + 1);
      let range = {start: start.toISOString(), end: end.toISOString()};
      for(let credset of result.data) {
        if(! credset.credentials) continue;
        if(credset.first_effective_date && credset.first_effective_date < range.start) {
          if (credset.first_effective_date < '0100-01-01') {
            range.start = '1970-01-01T00:00:00-00:00';
          } else {
            range.start = credset.first_effective_date;
          }
        }
        if(credset.last_effective_date && credset.last_effective_date > range.end) {
          range.end = credset.last_effective_date;
        }
        let row = {
          id: `set-${credset.id}`,
          slots: []
        };
        for(let cred of credset.credentials) {
          row.slots.push(this._formatter.getCredentialSlot(cred));
        }
        rows.push(row);
      }
      this._range = range;
      this._rows = rows;
    } else {
      this._rows = [];
    }
  }

  load() {
    if(this._loader && this._topicId) {
      this._dataService.loadList(this._loader, {parentId: this._topicId});
    }
  }
}
