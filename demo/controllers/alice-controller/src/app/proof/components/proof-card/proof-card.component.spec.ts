import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ProofCardComponent } from './proof-card.component';

describe('ProofCardComponent', () => {
  let component: ProofCardComponent;
  let fixture: ComponentFixture<ProofCardComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ProofCardComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ProofCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
