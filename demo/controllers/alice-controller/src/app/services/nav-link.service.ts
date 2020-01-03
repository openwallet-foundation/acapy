import { Injectable } from '@angular/core';

import { NavLink } from '../models/nav-link';

import navLinksJson from 'src/data/nav_links.json';

@Injectable({
  providedIn: 'root'
})
export class NavLinkService {
  navLinks: NavLink[] = [];

  constructor() {
    this.navLinks = navLinksJson.map((nav) => new NavLink(nav.label, nav.url));
  }

  getNavLinks(): NavLink[] {
    return this.navLinks;
  }

}
