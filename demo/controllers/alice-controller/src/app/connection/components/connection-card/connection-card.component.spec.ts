import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ConnectionCardComponent } from './connection-card.component';

describe('ConnectionCardComponent', () => {
  let component: ConnectionCardComponent;
  let fixture: ComponentFixture<ConnectionCardComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ConnectionCardComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ConnectionCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
