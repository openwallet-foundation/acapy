import { TestBed } from '@angular/core/testing';

import { AgentService } from './agent.service';

describe('AgentService', () => {
  beforeEach(() => TestBed.configureTestingModule({}));

  it('should be created', () => {
    const service: AgentService = TestBed.get(AgentService);
    expect(service).toBeTruthy();
  });
});
