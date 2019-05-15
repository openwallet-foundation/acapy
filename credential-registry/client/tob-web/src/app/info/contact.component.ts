import { Component } from '@angular/core';
import { GeneralDataService } from '../general-data.service';
import { catchError } from 'rxjs/operators';
import { _throw } from 'rxjs/observable/throw';


@Component({
  selector: 'app-contact',
  templateUrl: '../../themes/_active/info/contact.component.html',
  styleUrls: ['../../themes/_active/info/contact.component.scss']
})
export class ContactComponent {

  inited = true;
  feedback = {reason: '', from_name: '', from_email: '', comments: '', invalid: null};
  failed = false;
  sending = false;
  sent = false;

  constructor(
    private _dataService: GeneralDataService,
  ) {}

  checkFeedback(fb) {
    if(! fb.reason || ! fb.from_name || ! fb.from_email)
      return false;
    return true;
  }

  focusAlert(id) {
    setTimeout(() => {
      let alert = document.getElementById(id);
      if(alert) alert.focus();
    }, 50);
  }

  sendFeedback(evt) {
    if(evt) evt.preventDefault();
    if(this.sending) return;
    this.sending = true;
    this.sent = false;

    let fb = this.feedback;
    let valid = this.checkFeedback(fb);
    fb.invalid = valid ? null : 'required';
    if(! valid) {
      this.focusAlert('alert-required');
      this.sending = false;
      return;
    }

    let url = this._dataService.getRequestUrl('feedback');
    let result = this._dataService.postParams(url, fb);
    result.pipe(catchError(error => {
      this.failed = true;
      this.sending = false;
      this.focusAlert('alert-error');
      return _throw(error);
    })).subscribe(result => {
      this.sent = true;
      this.sending = false;
      this.focusAlert('alert-success');
      this.feedback = {reason: '', from_name: '', from_email: '', comments: '', invalid: null};
    });
  }

}
