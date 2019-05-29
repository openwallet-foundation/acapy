import { Component, OnInit, OnDestroy, AfterViewInit, ChangeDetectionStrategy } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AppConfigService } from 'app/app-config.service';
import { GeneralDataService } from 'app/general-data.service';
import { Fetch, Model } from '../data-types';
import { Subscription } from 'rxjs/Subscription';
import { TimelineFormatterService } from './timeline-formatter.service';

@Component({
  selector: 'cred-form',
  templateUrl: '../../themes/_active/cred/form.component.html',
  styleUrls: [
    '../../themes/_active/cred/cred.scss',
    '../../themes/_active/cred/form.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CredFormComponent implements OnInit, OnDestroy, AfterViewInit {
  id: number;
  claimsVisible: boolean = true;
  proofVisible: boolean = true;
  mode: string = 'view';
  _timelineRange: any;
  _timelineRows: any;

  private _loader = new Fetch.ModelLoader(Model.CredentialFormatted);
  private _verify = new Fetch.ModelLoader(Model.CredentialVerifyResult);
  private _idSub: Subscription;

  constructor(
    private _config: AppConfigService,
    private _dataService: GeneralDataService,
    private _route: ActivatedRoute,
    private _formatter: TimelineFormatterService,
  ) { }

  ngOnInit() {
    this._idSub = this._route.params.subscribe(params => {
      this.id = +params['credId'];
      this.mode = this._route.snapshot.data.verify ? 'verify' : 'view';
      this._dataService.loadRecord(this._loader, this.id, {primary: true});
    });
  }

  ngAfterViewInit() {
    this._loader.ready.subscribe(result => {
        this.updateRows();
        // auto-verify unless button is present
        let verify = this._config.getConfig().AUTO_VERIFY_CRED;
        if(verify === undefined || (verify && verify !== "false"))
          this.verifyCred();
    });
  }

  ngOnDestroy() {
    this._idSub.unsubscribe();
    this._loader.complete();
    this._verify.complete();
  }

  get result() {
    return this._loader.result;
  }

  get result$() {
    return this._loader.stream;
  }

  get verify$() {
    return this._verify.stream;
  }

  toggleShowClaims(evt?) {
    this.claimsVisible = !this.claimsVisible;
    if(evt) evt.preventDefault();
  }

  toggleShowProof(evt?) {
    this.proofVisible = !this.proofVisible;
    if(evt) evt.preventDefault();
  }

  verifyCred(evt?) {
    if(this.result.data.revoked)
      this._verify.reset();
    else
      this._dataService.loadRecord(this._verify, this.id);
  }

  updateRows() {
    let rows = [];
    let cred = <Model.Credential>this.result.data;
    let credset: Model.CredentialSet = cred.credential_set;
    let start = new Date();
    start.setFullYear(start.getFullYear() - 1);
    let end = new Date();
    end.setFullYear(end.getFullYear() + 1);
    let range = {start: start.toISOString(), end: end.toISOString()};
    if(credset) {
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
      this._timelineRange = range;
      this._timelineRows = rows;
    }
  }

  get timelineRange() {
    return this._timelineRange;
  }

  get timelineRows() {
    return this._timelineRows;
  }

}
