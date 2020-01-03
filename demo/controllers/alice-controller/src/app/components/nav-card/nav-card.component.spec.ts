import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { NavCardComponent } from './nav-card.component';

describe('CardComponent', () => {
  let component: NavCardComponent;
  let fixture: ComponentFixture<NavCardComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ NavCardComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(NavCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
