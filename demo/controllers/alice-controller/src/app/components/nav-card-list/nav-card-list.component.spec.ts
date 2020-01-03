import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { NavCardListComponent } from './nav-card-list.component';

describe('CardListComponent', () => {
  let component: NavCardListComponent;
  let fixture: ComponentFixture<NavCardListComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ NavCardListComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(NavCardListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
