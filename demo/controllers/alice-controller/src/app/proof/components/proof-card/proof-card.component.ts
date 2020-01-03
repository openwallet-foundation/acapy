import { Component, OnInit, Input } from '@angular/core';

@Component({
  selector: 'app-proof-card',
  templateUrl: './proof-card.component.html',
  styleUrls: ['./proof-card.component.scss']
})
export class ProofCardComponent implements OnInit {
  @Input() proof: any;

  constructor() { }

  ngOnInit() {
  }

}
