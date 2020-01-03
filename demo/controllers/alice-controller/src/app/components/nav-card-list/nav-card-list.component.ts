import { Component, OnInit } from '@angular/core';

import { NavLink } from 'src/app/models/nav-link';

import { NavLinkService } from 'src/app/services/nav-link.service';

@Component({
  selector: 'app-nav-card-list',
  templateUrl: './nav-card-list.component.html',
  styleUrls: ['./nav-card-list.component.scss']
})
export class NavCardListComponent implements OnInit {

  navLinks: NavLink[] = [];

  constructor(private navLinkService: NavLinkService) { }

  ngOnInit() {
    this.navLinks = this.navLinkService.getNavLinks();
  }

}
