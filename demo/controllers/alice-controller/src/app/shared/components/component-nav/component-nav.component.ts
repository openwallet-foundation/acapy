import { Component, OnInit } from '@angular/core';

import { NavLink } from 'src/app/models/nav-link';

import { NavLinkService } from 'src/app/services/nav-link.service';

@Component({
  selector: 'app-component-nav',
  templateUrl: './component-nav.component.html',
  styleUrls: ['./component-nav.component.scss']
})
export class ComponentNavComponent implements OnInit {
  moreNavLinks: NavLink[] = [];

  constructor(private navLinkService: NavLinkService) { }

  ngOnInit() {
    this.moreNavLinks = this.navLinkService.getNavLinks();
  }

}
