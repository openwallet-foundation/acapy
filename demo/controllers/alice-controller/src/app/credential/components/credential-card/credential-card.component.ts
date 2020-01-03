import { Component, OnInit, Input } from '@angular/core';

@Component({
  selector: 'app-credential-card',
  templateUrl: './credential-card.component.html',
  styleUrls: ['./credential-card.component.scss']
})
export class CredentialCardComponent implements OnInit {
  @Input() credential: any;

  constructor() { }

  ngOnInit() {
  }

}
