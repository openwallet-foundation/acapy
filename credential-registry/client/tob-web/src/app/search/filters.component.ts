import { Component, Input } from '@angular/core';
import { Fetch, Filter } from '../data-types';

@Component({
  selector: 'search-filters',
  templateUrl: '../../themes/_active/search/filters.component.html',
  styleUrls: ['../../themes/_active/search/filters.component.scss']
})
export class SearchFiltersComponent {

  @Input('filters') _filters : Filter.FieldSet;
  private _loading: boolean;

  get loading() {
    return this._loading;
  }

  @Input() set loading(val: boolean) {
    this._loading = val;
  }

  get filters$() {
    return this._filters.streamVisible;
  }

  get loaded() {
    return ! this._loading;
  }

  setFilter(evt, name: string, value) {
    let upd = {};
    if(evt && evt.target && evt.target.checked === false)
      value = null;
    upd[name] = value;
    upd['page'] = '1';
    this._filters.update(upd);
  }
}
