import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { CredentialListComponent } from './credential-list.component';

describe('CredentialListComponent', () => {
  let component: CredentialListComponent;
  let fixture: ComponentFixture<CredentialListComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ CredentialListComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(CredentialListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
