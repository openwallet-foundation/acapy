import { TestBed } from '@angular/core/testing';

import { ConnectionResolverService } from './connection-resolver.service';

describe('ConnectionResolverService', () => {
  beforeEach(() => TestBed.configureTestingModule({}));

  it('should be created', () => {
    const service: ConnectionResolverService = TestBed.get(ConnectionResolverService);
    expect(service).toBeTruthy();
  });
});
