import { AfterViewInit, ChangeDetectorRef, ChangeDetectionStrategy, Component, NgZone } from '@angular/core';

@Component({
  selector: 'app-pagescroll',
  templateUrl: '../../themes/_active/util/pagescroll.component.html',
  styleUrls: ['../../themes/_active/util/pagescroll.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  /*host: {
    '(window:scroll)': 'onScroll($event)',
  },*/
})
export class PageScrollComponent implements AfterViewInit {
  visible: boolean = false;

  constructor(private _zone: NgZone, private _cd: ChangeDetectorRef) {
  }

  ngAfterViewInit() {
    this._zone.runOutsideAngular(() => {
      window.addEventListener('scroll', this.onScroll.bind(this), { passive: true });
    });
  }

  scrollTop(evt?) {
    if(evt) evt.preventDefault();
    try {
      window.scrollTo({top: 0, left: 0, behavior: 'smooth'});
    } catch(e) {
      window.scrollTo(0, 0);
    }
  }

  onScroll(evt?) {
    let v = window.scrollY > 100;
    if(v != this.visible) {
      this.visible = v;
      this._cd.detectChanges();
    }
  }
}
