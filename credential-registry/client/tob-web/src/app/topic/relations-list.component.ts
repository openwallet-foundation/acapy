import { Component, EventEmitter, Input, Output, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { GeneralDataService } from '../general-data.service';
import { Fetch, Model } from '../data-types';
import { Subscription } from 'rxjs/Subscription';

@Component({
  selector: 'related-relationships',
  templateUrl: '../../themes/_active/topic/relations-list.component.html',
})
export class TopicRelatedListComponent implements OnInit, OnDestroy {
  protected _topicId: number;
  protected _defaultFormat = 'cards';
  @Input() title: string;
  @Input('related-from') relatedFrom: boolean;
  @Input('records') inputRecords: Model.TopicRelationship[];
  @Output() afterLoad = new EventEmitter<any>();
  loaded: boolean;
  loading: boolean;
  filterActive: string = 'true';

  private _loader: Fetch.ModelListLoader<Model.TopicRelationship>;

  constructor(
    private _dataService: GeneralDataService,
    private _route: ActivatedRoute,
    private _router: Router,
  ) {}

  ngOnInit() {
    this._loader = new Fetch.ModelListLoader(
      this.relatedFrom ? Model.TopicRelationshipRelatedFrom : Model.TopicRelationshipRelatedTo);
    this._loader.stream.subscribe(result => {
      this.loading = result.loading;
      this.loaded = result.loaded;
      if(result.loaded || result.error) {
        this.afterLoad.emit(result.loaded);
      }
    });
    this.load();
  }

  ngOnDestroy() {
    this._loader.complete();
  }

  @Input() set defaultFormat(fmt: string) {
    this._defaultFormat = fmt;
  }

  get defaultFormat(): string {
    return this._defaultFormat;
  }

  get format(): string {
    // switch to list for many records
    return this._defaultFormat;
  }

  get topicId(): number {
    return this._topicId;
  }

  @Input() set topicId(newId: number) {
    this._topicId = newId;
    this.load();
  }

  load() {
    if(this._loader && this._topicId && ! this.inputRecords)
      this._dataService.loadList(this._loader, {parentId: this._topicId});
  }

  get topics(): Model.TopicRelationship[] {
    return this.inputRecords || this._loader.result.data;
  }
}
