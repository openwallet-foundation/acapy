import { Component, OnInit, Input } from '@angular/core';

import { NavLink } from 'src/app/models/nav-link';

@Component({
  selector: 'app-nav-card',
  templateUrl: './nav-card.component.html',
  styleUrls: ['./nav-card.component.scss']
})
export class NavCardComponent implements OnInit {
  @Input() navLink: NavLink;

  constructor() { }

  ngOnInit() {
  }

}
