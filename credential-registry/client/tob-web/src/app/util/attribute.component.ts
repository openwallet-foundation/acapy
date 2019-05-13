import { Component, Input } from '@angular/core';
import { Model } from '../data-types';
import { TranslateService } from '@ngx-translate/core';
import { map } from 'rxjs/operators';
import { GeneralDataService } from '../general-data.service';

@Component({
  selector: 'attribute-view',
  templateUrl: '../../themes/_active/util/attribute.component.html',
  styleUrls: ['../../themes/_active/cred/cred.scss']
})
export class AttributeComponent {

  @Input() record: Model.Attribute;
  @Input('format') _format: string;

  constructor(
    private _dataService: GeneralDataService,
    private _translate: TranslateService,
  ) {}

  get format(): string {
    return this._format === undefined ? (this.record && this.record.format) : this._format;
  }

  get formatted(): string {
    return this.record.value;
  }

  get categoryValue() {
    return this._dataService.translateCategoryLabel(
      this.record.credential_type_id, this.record.type, this.record.value);
  }

  get jurisdictionValue() {
    let val = this.record.value;
    if(val) {
      let usState = val.match(/^\s*US[, \-]+([A-Z]{2})\s*$/i);
      if(usState) {
        let stateLbl = 'jurisdiction.us_states.' + usState[1].toUpperCase();
        let usLbl = 'jurisdiction.general.US';
        return this._translate.stream([stateLbl, usLbl]).pipe(map(
          lbls => {
            if(lbls[stateLbl] && lbls[stateLbl] != stateLbl && lbls[stateLbl].substring(0, 2) != '??') {
              return lbls[stateLbl] + ', ' + lbls[usLbl];
            }
            return val;
          }
        ));
      } else {
        let provLbl = 'jurisdiction.provinces.' + val.toUpperCase();
        let extLbl = 'jurisdiction.general.' + val.toUpperCase();
        return this._translate.stream([provLbl, extLbl]).pipe(map(
          lbls => {
            if(lbls[provLbl] && lbls[provLbl] != provLbl && lbls[provLbl].substring(0, 2) != '??')
              return lbls[provLbl];
            else if(lbls[extLbl] && lbls[extLbl] != extLbl && lbls[extLbl].substring(0, 2) != '??')
              return lbls[extLbl];
            return val;
          }
        ));
      }
    }
  }

  get numberValue() {
    let val = this.record.value;
    let match = val && val.match(/^(\d+)(\.\d+)?$/);
    if(match) {
      val = new Number(match[1]).toLocaleString() + match[2];
    }
    return val;
  }
}
