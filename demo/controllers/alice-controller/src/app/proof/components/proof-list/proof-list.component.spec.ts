import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ProofListComponent } from './proof-list.component';

describe('ProofListComponent', () => {
  let component: ProofListComponent;
  let fixture: ComponentFixture<ProofListComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ProofListComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ProofListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
