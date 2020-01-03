import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ProofComponent } from './proof.component';

describe('ProofComponent', () => {
  let component: ProofComponent;
  let fixture: ComponentFixture<ProofComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ProofComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ProofComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
