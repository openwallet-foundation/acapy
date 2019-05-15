import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Fetch } from '../data-types';

@Component({
  selector: 'search-nav',
  templateUrl: '../../themes/_active/search/nav.component.html',
  styleUrls: ['../../themes/_active/search/nav.component.scss']
})
export class SearchNavComponent {

  @Input() info : Fetch.ListInfo;
  private _loading : boolean;
  @Output() nav = new EventEmitter<string>();
  @Input('status') showStatus : any;
  @Input('buttons') showButtons = true;

  get enabled() : boolean {
    return !! this.info && ! this.loading;
  }

  get havePrevious() {
    return this.info && this.info.havePrevious;
  }

  get haveNext() {
    return this.info && this.info.haveNext;
  }

  get pageNumber() {
    return this.info.pageNum;
  }

  get loading() {
    return this._loading;
  }

  @Input() set loading(val: boolean) {
    this._loading = val;
  }

  get loaded() {
    return ! this._loading && this.info;
  }

  performNav(evt, nav: string) {
    if(evt) evt.preventDefault();
    this.nav.emit(nav);
  }
}
