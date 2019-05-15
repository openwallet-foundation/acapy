import {
  Component, Input, AfterViewInit, OnDestroy,
  NgZone, ChangeDetectorRef,
  ElementRef, Renderer2, ViewChild,
} from '@angular/core';
import { Router } from '@angular/router';
import { Model } from '../data-types';
import { Timeline } from '../timeline/timeline';

@Component({
  selector: 'timeline-view',
  template: `<div #outer></div>`,
  styleUrls: [
    '../../themes/_active/timeline/timeline.scss',
  ],
  /*host: {
    '(window:resize)': 'onResize($event)',
  },*/
})
export class TimelineViewComponent implements AfterViewInit, OnDestroy {
  @ViewChild('outer') private _outer: ElementRef;
  private _timeline: Timeline.TimelineView;
  private _range: {start: (string | Date), end: (string | Date)};
  private _resizeHook: null;
  private _rows: Timeline.RowSpec[] = [];

  constructor(
    private _cd: ChangeDetectorRef,
    private _renderer: Renderer2,
    private _router: Router,
    private _zone: NgZone,
  ) { }

  ngAfterViewInit() {
    this._timeline = new Timeline.TimelineView(this._outer.nativeElement, null, this._renderer);
    this._timeline.setRange(this.rangeStart, this.rangeEnd);
    this._timeline.setRows(this.rows);
    this._timeline.setMarkers([
      {date: new Date(), label: 'Today'}
    ]);
    this._renderer.listen(this._timeline.container, 'slotclick', this.click.bind(this));
    this._zone.runOutsideAngular(() => {
      this._timeline.render();
      this._resizeHook = this.onResize.bind(this);
      window.addEventListener('resize', this._resizeHook, {passive: true});
    });
  }

  ngOnDestroy() {
    this._zone.runOutsideAngular(() => {
      if(this._resizeHook)
        window.removeEventListener('resize', this._resizeHook);
    });
  }

  click(evt) {
    this._router.navigate([evt.detail.spec.url]);
  }

  get rangeStart() {
    if(! this._range || ! this._range.start) {
      let d = new Date();
      d.setFullYear(d.getFullYear() - 1);
      return d.toISOString();
    }
    return this._range.start;
  }

  get rangeEnd() {
    if(! this._range || ! this._range.end) {
      let d = new Date();
      d.setFullYear(d.getFullYear() + 1);
      return d.toISOString();
    }
    return this._range.end;
  }

  get range() {
    return {start: this.rangeStart, end: this.rangeEnd};
  }

  @Input() set range(rng: {start: (string | Date), end: (string | Date)}) {
    if(rng.start && rng.end) {
      // expand range
      let start = Timeline.parseDate(rng.start);
      let end = Timeline.parseDate(rng.end);
      let diff = end.getTime() - start.getTime();
      let offs = diff * 0.1;
      start.setTime(start.getTime() - offs);
      end.setTime(end.getTime() + offs);
      rng.start = start.toISOString();
      rng.end = end.toISOString();
    }
    this._range = rng;
    if(this._timeline)
      this._timeline.setRange(this.rangeStart, this.rangeEnd);
  }

  get rows() {
    return this._rows;
  }

  @Input() set rows(vals: Timeline.RowSpec[]) {
    this._rows = vals;
    if(this._timeline)
      this._timeline.setRows(this.rows);
  }

  onResize(evt?) {
    if(this._timeline)
      this._timeline.update();
  }

  get testdata(): Timeline.RowSpec[] {
    let rows = [];
    rows.push(
      {
        id: 'set-1',
        slots: [
          {
            id: 'slot-1a',
            groups: ['all'],
            htmlContent: '<strong>Testing</strong>,<br>testing',
            start: '2018-06-01T00:00:00Z',
            end: '2020-05-31T00:00:00Z',
            classNames: ['slot-primary'],
          },
          {
            id: 'slot-1b',
            groups: ['all'],
            htmlContent: '<strong>Testing</strong>,<br>testing',
            start: '2020-05-31T00:00:00Z',
            end: '2021-05-31T00:00:00Z',
            classNames: ['slot-secondary'],
          }
        ]
      }
    );
    rows.push(
      {
        id: 'set-2',
        slots: [
          {
            id: 'slot-2',
            groups: ['all'],
            htmlContent: 'Hello there',
            start: '2020-03-15T00:00:00Z',
            end: '2030-05-31T00:00:00Z',
            classNames: ['slot-primary'],
          }
        ]
      }
    );
    return rows;
  }

}
