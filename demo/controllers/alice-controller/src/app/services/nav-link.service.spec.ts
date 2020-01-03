import { TestBed } from '@angular/core/testing';

import { NavLinkService } from './nav-link.service';

describe('NavLinkService', () => {
  beforeEach(() => TestBed.configureTestingModule({}));

  it('should be created', () => {
    const service: NavLinkService = TestBed.get(NavLinkService);
    expect(service).toBeTruthy();
  });
});
