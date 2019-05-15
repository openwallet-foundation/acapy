import { Component, Input } from '@angular/core';
import { Model } from '../data-types';

@Component({
  selector: 'address-view',
  template: `<div *ngIf="record" class="claim-info location" [innerHTML]="formatted"></div>`,
  styleUrls: ['../../themes/_active/cred/cred.scss']
})
export class AddressComponent {

  @Input() record: Model.Address;

  get formatted(): string {
    let addr = this.record;

    if(! addr) return '';
    let lines = [
      this.haveCivicAddress ? addr.civic_address :'' ,
      this.haveCity && this.haveProvince ? addr.city + ', ' + addr.province : addr.city || addr.province,
      this.haveCountry && this.havePostalCode ? addr.country + '&nbsp; ' + addr.postal_code : addr.country || addr.postal_code,
    ];
    return lines.filter((line) => line !== null).join('<br>');
  }

  get haveCivicAddress(): boolean {
    return this.record && this.record.civic_address && this.record.civic_address !== null && this.record.civic_address.trim().length > 0;
  }

  get haveCity(): boolean {
    return this.record && this.record.city && this.record.city !== null && this.record.city.trim().length > 0;
  }

  get haveProvince(): boolean {
    return this.record && this.record.province && this.record.province !== null && this.record.province.trim().length > 0;
  }

  get haveCountry(): boolean {
    return this.record && this.record.country && this.record.country !== null && this.record.country.trim().length > 0;
  }

  get havePostalCode(): boolean {
    return this.record && this.record.postal_code && this.record.postal_code !== null && this.record.postal_code.trim().length > 0;
  }

  ngOnInit() {
  }

}
