import { Component, Input, OnInit } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'app-sharelink',
  templateUrl: '../../themes/_active/util/share-link.component.html',
  styleUrls: ['../../themes/_active/util/share-link.component.scss'],
})
export class ShareLinkComponent implements OnInit {
  @Input() link: string[];
  protected _modal = null;
  protected copied: boolean;

  constructor(
    private _modalService: NgbModal,
  ) {
  }

  ngOnInit() {
    this.copied = false;
  }

  get shareLink() {
    if(this.link) {
      return location.origin + this.link.join('');
    }
  }

  copyShareLink(input) {
    if(input) {
      input.select();
      document.execCommand('copy');
      this.copied = true;
    }
  }

  openModal(content, evt?) {
    this._modal = this._modalService.open(content, { size: 'lg' });
    if(evt) evt.preventDefault();
  }

  dismissModal(reason?) {
    if(this._modal) this._modal.dismiss(reason);
  }

}
