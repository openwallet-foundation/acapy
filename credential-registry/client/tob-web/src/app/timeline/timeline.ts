import { Renderer2 } from '@angular/core';

export namespace Timeline {

  const YEAR_LEN = 31536000000;

  function clearChildNodes(elt: Node, fromIdx?: number) {
    if(! elt) return;
    for(var i = elt.childNodes.length-1; i >= (fromIdx || 0); i--) {
      elt.removeChild(elt.childNodes[i]);
    }
  }

  function addElementContent(elt, content) {
    if(typeof content === 'string') {
      elt.appendChild(document.createTextNode(content));
    } else if(elt) {
      elt.appendChild(content);
    }
  }

  function setElementContent(elt, content) {
    if(typeof content === 'string')
      elt.innerHTML = content;
    else if(Array.isArray(content)) {
      elt.innerHTML = '';
      for(let part of content) {
        addElementContent(elt, part);
      }
    }
  }

  export function parseDate(date: string | Date) {
    let result: Date = null;
    if(typeof date === 'string')
      result = new Date(date);
    else
      result = date;
    if(result && isNaN(result.getTime()))
      result = null;
    return result;
  }

  function offsetDate(date: Date, offset: number) {
    let time = date.getTime() + (offset || 0);
    let d = new Date();
    d.setTime(time);
    return d;
  }

  export interface Layout {
    start?: Date;
    end?: Date;
    width?: number;
    menuPos?: string;
    rowScale?: number;
    noAnimate?: boolean;
    time?: number;
  }

  export interface MarkerSpec {
    classNames?: string[];
    date: Date;
    label?: string;
  }

  export interface RowSpec {
    slots: SlotSpec[];
    classNames?: string[];
    height?: number;
  }

  export interface SlotSpec {
    groups: string[];
    start: Date;
    end: Date;
    htmlContent: string | (string | Node)[];
    classNames?: string[];
    url?: string;
    data?: string;
  }

  class Marker {
    date: Date;
    classNames: string[];
    label: string;
    start: Date;
    end: Date;
    _elt: HTMLElement;
    _labelElt: HTMLElement;
    _renderer: Renderer2;

    constructor(spec?: MarkerSpec) {
      if(spec) {
        this.classNames = spec.classNames;
        this.date = spec.date;
        this.label = spec.label;
      }
    }

    setRange(start: Date, end: Date) {
      this.start = start;
      this.end = end;
    }

    render(renderer: Renderer2) {
      this._renderer = renderer;
      if(! this._elt) {
        this._elt = renderer.createElement('div');
        renderer.addClass(this._elt, 'timeline-marker');
        if(this.classNames) {
          for(let c of this.classNames) {
            renderer.addClass(this._elt, c);
          }
        }
        if(this.label) {
          this._labelElt = renderer.createElement('label');
          this._labelElt.appendChild(document.createTextNode(this.label));
          this._elt.appendChild(this._labelElt);
        }
      }
      return this._elt;
    }

    update(width) {
      let hide = true;
      if(this.start && this.end && this.date && width) {
        let startTime = this.start.getTime();
        let endTime = this.end.getTime();
        let markTime = this.date.getTime();
        if(markTime >= startTime && markTime < endTime) {
          hide = false;
          let pos = Math.round((markTime - startTime) * width / (endTime - startTime)) - 1;
          this._elt.style.left = '' + pos + 'px';
        }
      }
      this._elt.style.display = hide ? 'none' : null;
    }
  }

  class Row {
    slots: Slot[] = [];
    classNames: string[];
    height: number;
    start: Date;
    end: Date;
    _elt: HTMLElement;
    _renderer: Renderer2;
    _next: HTMLElement;
    _prev: HTMLElement;

    constructor(spec?: RowSpec) {
      if(spec) {
        this.classNames = spec.classNames;
        this.height = spec.height;
        this.setSlots(spec.slots);
      }
    }

    setSlots(specs: SlotSpec[]) {
      if(specs) {
        this.slots = specs.map(evt => new Slot(evt));
      } else {
        this.slots = [];
      }
    }

    setRange(start: Date, end: Date) {
      this.start = start;
      this.end = end;
    }

    get elt() {
      return this._elt;
    }

    render(renderer: Renderer2) {
      this._renderer = renderer;
      if(! this._elt) {
        this._elt = renderer.createElement('div');
        renderer.addClass(this._elt, 'timeline-row');
        if(this.classNames) {
          for(let c of this.classNames) {
            renderer.addClass(this._elt, c);
          }
        }
      }
      return this._elt;
    }

    update(width) {
      if(this.start && this.end && width) {
        let startTime = this.start.getTime();
        let endTime = this.end.getTime();
        let range = endTime - startTime;
        let havePrev = false;
        let haveNext = false;
        // determine visible slots and compute offsets
        for(let evt of this.slots) {
          let elt = evt.render(this._renderer);
          let startPos = -1;
          let endPos = width + 1;
          let updState = {'hovered': false, 'started': false, 'ended': false};

          if(evt.start) {
            let evtStart = evt.start.getTime();
            if(evtStart < startTime)
              havePrev = true;
            if(evtStart > endTime) {
              haveNext = true;
              if(elt.parentNode) elt.parentNode.removeChild(elt);
              continue;
            }
            startPos = Math.round((Math.max(startTime, evtStart) - startTime) * width / range) - 1;
            if(startPos > 0)
              updState['started'] = true;
          }
          elt.style.left = '' + startPos + 'px';

          if(evt.end) {
            let evtEnd = evt.end.getTime();
            if(evtEnd > endTime)
              haveNext = true;
            if(evtEnd < startTime) {
              havePrev = true;
              if(elt.parentNode) elt.parentNode.removeChild(elt);
              continue;
            }
            endPos = Math.round((Math.min(endTime, evtEnd) - startTime) * width / range) + 1;
            if(endPos < width)
              updState['ended'] = true;
          }
          evt.updateState(updState);
          elt.style.width = '' + Math.max(endPos - startPos, 1) + 'px';
          this.elt.appendChild(elt);
        }
        if(havePrev) {
          if(! this._prev) {
            let link = this._renderer.createElement('div');
            this._renderer.addClass(link, 'fa');
            this._renderer.addClass(link, 'fa-caret-right');
            this._renderer.addClass(link, 'prev-link');
            link.tabIndex = 0;
            this._prev = link;
          }
          this.elt.appendChild(this._prev);
        } else if(this._prev && this._prev.parentNode) {
          this._prev.parentNode.removeChild(this._prev);
        }
        if(haveNext) {
          if(! this._next) {
            let link = this._renderer.createElement('div');
            this._renderer.addClass(link, 'fa');
            this._renderer.addClass(link, 'fa-caret-left');
            this._renderer.addClass(link, 'next-link');
            link.tabIndex = 0;
            this._next = link;
          }
          this.elt.appendChild(this._next);
        } else if(this._next && this._next.parentNode) {
          this._next.parentNode.removeChild(this._next);
        }
      }
    }
  }

  class SlotState {
    active: boolean = false;
    focused: boolean = false;
    hovered: boolean = false;
    started: boolean = false;
    ended: boolean = false;
  }

  class Slot {
    _elt: HTMLElement;
    _renderer: Renderer2;
    _spec: SlotSpec;
    _state: SlotState = new SlotState();
    start: Date;
    end: Date;

    constructor(spec: SlotSpec) {
      this._spec = spec;
      this.start = parseDate(this._spec.start);
      this.end = parseDate(this._spec.end);
    }

    get elt() {
      return this._elt;
    }

    get spec() {
      return this._spec;
    }

    handleEvent(evt) {
      if(evt.target === this._elt) {
        let update = true;
        if(evt.type === 'focus')
          this._state.focused = true;
        else if(evt.type === 'blur')
          this._state.focused = false;
        else if(evt.type === 'mouseenter')
          this._state.hovered = true;
        else if(evt.type === 'mouseleave')
          this._state.hovered = false;
        else
          update = false;
        if(update)
          this.updateState();
      }
      if(evt.type === 'click') {
        evt.preventDefault();
        let raise = new CustomEvent('slotclick', {detail: this, bubbles: true});
        this._elt.dispatchEvent(raise);
      }
    }

    setState(state, val) {
      this._state[state] = val;
      this.updateState();
    }

    updateState(state?) {
      if(state) {
        Object.assign(this._state, state);
      }
      let classes = {
        'active': this._state.active,
        'focus': this._state.focused,
        'hover': this._state.hovered,
        'started': this._state.started,
        'ended': this._state.ended,
      }
      for(let k in classes) {
        if(classes[k])
          this._renderer.addClass(this._elt, k);
        else
          this._renderer.removeClass(this._elt, k);
      }
    }

    render(renderer: Renderer2) {
      this._renderer = renderer;
      if(! this._elt) {
        this._elt = renderer.createElement(this._spec.url ? 'a' : 'div');
        renderer.addClass(this._elt, 'timeline-slot');
        this._elt.tabIndex = 0;
        if(this._spec.url)
          this._elt.setAttribute('href', this._spec.url);
        let handler = this.handleEvent.bind(this);
        this._elt.addEventListener('mouseenter', handler, false);
        this._elt.addEventListener('mouseleave', handler, false);
        this._elt.addEventListener('focus', handler, false);
        this._elt.addEventListener('blur', handler, false);
        this._elt.addEventListener('click', handler, false);
        if(this._spec.classNames) {
          for(let c of this._spec.classNames) {
            renderer.addClass(this._elt, c);
          }
        }
      }
      clearChildNodes(this._elt);
      let content = renderer.createElement('div');
      renderer.addClass(content, 'content');
      setElementContent(content, this._spec.htmlContent);
      this._elt.appendChild(content);
      return this._elt;
    }
  }

  class Axis {
    start: Date;
    end: Date;
    _elt: HTMLElement;
    _renderer: Renderer2;
    _ticks: HTMLElement[] = [];

    render(renderer: Renderer2) {
      this._renderer = renderer;
      if(! this._elt) {
        this._elt = renderer.createElement('div');
        renderer.addClass(this._elt, 'timeline-axis');
      }
      return this._elt;
    }

    setRange(start: Date, end: Date) {
      this.start = start;
      this.end = end;
    }

    update(width) {
      clearChildNodes(this._elt);
      if(this.start && this.end && width) {
        let inc = 1;
        let startYear = this.start.getFullYear();
        let startTime = this.start.getTime();
        let endTime = this.end.getTime();
        let range = endTime - startTime;
        let yearStep = 1;
        let subtick = 0;
        let slotWidth = width / (range / YEAR_LEN);
        if(slotWidth > 200)
          subtick = 11;
        else if(slotWidth > 100)
          subtick = 3;
        else if(slotWidth > 50)
          subtick = 1;
        else if(slotWidth > 20)
          yearStep = subtick = 2;
        else if(slotWidth > 10)
          yearStep = subtick = 5;
        else if(slotWidth > 7)
          yearStep = subtick = 10;
        else {
          yearStep = 25;
          subtick = 5;
        }
        startYear -= startYear % yearStep;
        let tickidx = 0;
        let dt = new Date(startYear, 0, 1);
        let endYear = this.end.getFullYear() + yearStep * 2;
        for(let year = startYear; year <= endYear; year += yearStep) {
          let next = new Date(year + yearStep, 0, 1);
          let pos = (dt.getTime() - startTime) * width / range;
          if(pos > width) break;
          if(pos > 0) {
            let tick = this._ticks[tickidx++];
            if(! tick) {
              tick = this._renderer.createElement('div');
              this._renderer.addClass(tick, 'tick');
              this._ticks.push(tick);
            }
            this._renderer.removeClass(tick, 'small');
            tick.style.left = '' + Math.round(pos) + 'px';
            this._elt.appendChild(tick);
          }

          let nextpos = (next.getTime() - startTime) * width / range;
          for(let i = 0; i < subtick; i++) {
            let tpos = pos + (nextpos - pos) * (i + 1) / (subtick + 1);
            if(tpos < 0) continue;
            let tick = this._ticks[tickidx++];
            if(! tick) {
              tick = this._renderer.createElement('div');
              this._renderer.addClass(tick, 'tick');
              this._ticks.push(tick);
            }
            this._renderer.addClass(tick, 'small');
            tick.style.left = '' + Math.round(tpos) + 'px';
            this._elt.appendChild(tick);
          }

          let date = this._renderer.createElement('div');
          this._renderer.addClass(date, 'date');
          setElementContent(date, ['' + dt.getFullYear()]);
          date.style.left = '' + Math.round(pos) + 'px';
          this._elt.appendChild(date);

          dt = next;
        }
      }
    }
  }

  export class TimelineView {
    _elts: {[key: string]: HTMLElement} = {
      container: null,
      controlsOuter: null,
      controlsInner: null,
      axisOuter: null,
      rowsOuter: null,
    };
    _axis: Axis;
    _layout: Layout = {};
    _lastLayout: Layout;
    _nextLayout: Layout;
    _gestureStartLayout: Layout;
    _markers: Marker[] = [];
    _rendered: boolean = false;
    _renderer: Renderer2;
    _resetRange : {start: Date, end: Date};
    _rows: Row[] = [];
    _redrawTimer: number;
    _updateTimer: number;

    constructor(container: HTMLElement, layout: Layout, renderer: Renderer2) {
      this._elts.container = container;
      this._layout = layout || {};
      this._renderer = renderer;
    }

    get container() {
      return this._elts.container;
    }

    get rows() {
      return this._rows;
    }

    setRows(vals: RowSpec[]) {
      this._rows = (vals || []).map(val => new Row(val));
      this.redraw();
    }

    setMarkers(vals: MarkerSpec[]) {
      this._markers = (vals || []).map(val => new Marker(val));
      this.redraw();
    }

    setRange(start: string | Date, end: string | Date, relative?: boolean) {
      let startDate = parseDate(start);
      let endDate = parseDate(end);
      if(startDate && endDate && endDate.getTime() < startDate.getTime()) {
        // swap if in wrong order
        let dt = startDate;
        startDate = endDate;
        endDate = dt;
      }
      let layout = Object.assign({}, this._layout);
      layout.start = startDate;
      layout.end = endDate;
      if(! relative)
        this._resetRange = {start: startDate, end: endDate};
      this.setLayout(layout);
    }

    moveRange(delta, layout?: Layout) {
      if(! layout) layout = this._layout;
      if(layout.start && layout.end) {
        let startTime = layout.start.getTime();
        let diff = layout.end.getTime() - startTime;
        startTime -= Math.round(diff * delta / 300);
        let start = new Date();
        start.setTime(startTime);
        let end = offsetDate(start, diff);
        this.setRange(start, end, true);
      }
    }

    scaleRange(delta, layout?: Layout) {
      if(! layout) layout = this._layout;
      if(layout.start && layout.end) {
        let startTime = layout.start.getTime();
        let diff = layout.end.getTime() - startTime;
        let offs = Math.round(diff * delta);
        if(diff + offs * 2 > YEAR_LEN * 200) {
          offs = (YEAR_LEN * 200 - diff) / 2;
        }
        let start = offsetDate(layout.start, -offs);
        let end = offsetDate(layout.end, +offs);
        this.setRange(start, end, true);
      }
    }

    resetRange() {
      if(this._resetRange) {
        let layout = Object.assign({}, this._layout);
        layout.start = this._resetRange.start;
        layout.end = this._resetRange.end;
        this.setLayout(layout);
      }
    }

    get layout() {
      return this._layout;
    }

    setLayout(newLayout: Layout) {
      if (! newLayout) return;
      if (this._layout && ! newLayout.noAnimate && this._rendered
          && newLayout.start && newLayout.end && this._layout.start && this._layout.end) {
        if(! newLayout.time)
          newLayout.time = new Date().getTime() + 200;
        this._lastLayout = this._layout;
        this._lastLayout.time = new Date().getTime();
        this._nextLayout = newLayout;
        this.update();
      }
      else {
        newLayout.time = new Date().getTime();
        this._lastLayout = this._layout;
        this._layout = newLayout;
        this._nextLayout = null;
        this.redraw();
      }
    }

    handleEvent(evt) {
      if(evt.type === 'mousewheel') {
        if (evt.ctrlKey) {
          if(evt.deltaY) {
            let delta = evt.deltaY * 0.01;
            this.scaleRange(delta);
            evt.preventDefault();
          }
        } else {
          if(Math.abs(evt.deltaX) > Math.abs(evt.deltaY)) {
            let delta = - evt.deltaX * 2;
            delta = Math.sign(delta) * Math.min(Math.abs(delta), 50);
            this.moveRange(delta);
            evt.preventDefault();
          }
        }
      }
      else if(evt.type === 'gesturestart') {
        evt.preventDefault();
        evt.stopPropagation();
        this._gestureStartLayout = Object.assign({}, this._layout);
      }
      else if(evt.type === 'gesturechange') {
        evt.preventDefault();
        evt.stopPropagation();
        if(evt.scale) {
          this.scaleRange(- evt.scale, this._gestureStartLayout);
        }
      }
      else if(evt.type === 'gestureend') {
        evt.preventDefault();
        this._gestureStartLayout = null;
      }
    }

    handleControl(evt) {
      let tgt = evt.target;
      while(tgt && ! tgt.name && tgt.parentNode && tgt.parentNode !== window)
        tgt = tgt.parentNode;
      let evtName = tgt && tgt.name;
      if(evtName == 'zoomin') {
        this.scaleRange(-0.1);
      }
      else if(evtName == 'zoomout') {
        this.scaleRange(0.1);
      }
      else if(evtName == 'prev') {
        this.moveRange(10);
      }
      else if(evtName == 'fastprev') {
        this.moveRange(100);
      }
      else if(evtName == 'next') {
        this.moveRange(-10);
      }
      else if(evtName == 'fastnext') {
        this.moveRange(-100);
      }
      else if(evtName == 'reset') {
        this.resetRange();
      }
    }

    render() {
      let rdr = this._renderer;
      let elts = this._elts;
      if(rdr && ! this._rendered) {
        if (! elts.container) {
          elts.container = rdr.createElement('div');
        }
        let handler = this.handleEvent.bind(this);
        rdr.listen(elts.container, 'mousewheel', handler);
        rdr.listen(elts.container, 'gesturestart', handler);
        rdr.listen(elts.container, 'gesturechange', handler);
        rdr.listen(elts.container, 'gestureend', handler);
        // disable forward/back gesture in Chrome
        rdr.listen(elts.container, 'pointermove', handler);
        rdr.addClass(elts.container, 'timeline-outer');
        elts.controlsOuter = rdr.createElement('div');
        rdr.addClass(elts.controlsOuter, 'controls-outer');
        rdr.addClass(elts.controlsOuter, 'row');
        elts.controlsInner = rdr.createElement('div');
        rdr.addClass(elts.controlsInner, 'controls-inner');
        rdr.addClass(elts.controlsInner, 'col');
        rdr.addClass(elts.controlsInner, 'text-center');
        elts.controlsOuter.appendChild(elts.controlsInner);
        this.renderControls();
        elts.rowsOuter = rdr.createElement('div');
        rdr.addClass(elts.rowsOuter, 'rows-outer');
        elts.axisOuter = rdr.createElement('div');
        rdr.addClass(elts.axisOuter, 'axis-outer');
        this._axis = new Axis();
        this._axis.setRange(this._layout.start, this._layout.end);
        elts.axisOuter.appendChild(this._axis.render(rdr));
        this._rendered = true;
        this.redraw();
      }
      return elts.container;
    }

    renderControls() {
      let groups = [
        ['fastprev', 'prev'],
        ['zoomout', 'zoomin'],
        ['reset'],
        ['next', 'fastnext'],
      ];
      let icons = {
        fastprev: 'fa-angle-double-left',
        prev: 'fa-angle-left',
        zoomin: 'fa-search-plus',
        zoomout: 'fa-search-minus',
        reset: 'fa-undo',
        next: 'fa-angle-right',
        fastnext: 'fa-angle-double-right',
      };
      let rdr = this._renderer;
      for(let btns of groups) {
        let grp = rdr.createElement('div');
        rdr.addClass(grp, 'btn-group');
        grp.setAttribute('role', 'group');
        for(let btn of btns) {
          let elt = rdr.createElement('button');
          elt.setAttribute('type', 'button');
          rdr.addClass(elt, 'btn');
          rdr.addClass(elt, 'btn-sm');
          rdr.addClass(elt, 'btn-secondary');
          elt.name = btn;
          elt.tabIndex = 0;
          let icon = rdr.createElement('span');
          rdr.addClass(icon, 'fa');
          rdr.addClass(icon, icons[btn]);
          elt.appendChild(icon);
          grp.appendChild(elt);
          rdr.listen(elt, 'click', this.handleControl.bind(this));
        }
        this._elts.controlsInner.appendChild(grp);
        this._elts.controlsInner.appendChild(document.createTextNode(' '));
      }
    }

    redraw() {
      if (! this._rendered) return;
      clearTimeout(this._updateTimer);
      this._updateTimer = null;
      if (this._redrawTimer) return;
      this._redrawTimer = requestAnimationFrame(this._performRedraw.bind(this));
    }

    _performRedraw() {
      let container = this._elts.container;
      let first = container.childNodes[0];
      let body = [this._elts.controlsOuter, this._elts.rowsOuter, this._elts.axisOuter];
      for(let elt of body) {
        container.insertBefore(elt, first);
      }
      clearChildNodes(container, body.length);
      let rowFirst = this._elts.rowsOuter.childNodes[0];
      let zIndex = 40;
      let clearPos = 0;
      for(let mark of this._markers) {
        let elt = mark.render(this._renderer);
        this._elts.rowsOuter.insertBefore(elt, rowFirst);
        // elt.style.zIndex = '' + Math.max(0, zIndex);
        clearPos ++;
      }
      for(let row of this._rows) {
        let elt = row.render(this._renderer);
        this._elts.rowsOuter.insertBefore(elt, rowFirst);
        elt.style.zIndex = '' + Math.max(0, zIndex--);
        clearPos ++;
      }
      clearChildNodes(this._elts.rowsOuter, clearPos);
      this._performUpdate();
    }

    update() {
      if(this._updateTimer) return;
      this._updateTimer = requestAnimationFrame(this._performUpdate.bind(this));
    }

    _updateLayout() {
      if(this._nextLayout) {
        let now = new Date().getTime();
        if(this._nextLayout.time <= now) {
          this._nextLayout.time = now;
          this._layout = this._nextLayout;
          this._nextLayout = null;
        } else {
          // move closer to layout
          let startTime = this._lastLayout.time;
          let diff = this._nextLayout.time - startTime;
          let scale = (now - startTime) / diff;
          if(this._nextLayout.start != this._lastLayout.start)
            this._layout.start = offsetDate(this._lastLayout.start, diff * scale);
          if(this._nextLayout.end != this._lastLayout.end)
            this._layout.end = offsetDate(this._lastLayout.end, diff * scale);
          return false;
        }
      }
      return true;
    }

    _performUpdate() {
      clearTimeout(this._updateTimer);
      this._updateTimer = null;
      let reUp = ! this._updateLayout();
      if(this._elts.container) {
        let width = this._elts.container.clientWidth;

        // reposition slots
        let rowsWidth = this._elts.rowsOuter.clientWidth;
        for(let row of this._rows) {
          row.setRange(this._layout.start, this._layout.end);
          row.update(rowsWidth);
        }

        // redraw axis
        let axisWidth = this._elts.axisOuter.clientWidth;
        this._axis.setRange(this._layout.start, this._layout.end);
        this._axis.update(axisWidth);

        // reposition markers
        for(let mark of this._markers) {
          mark.setRange(this._layout.start, this._layout.end);
          mark.update(rowsWidth);
        }
      }
      if(reUp)
        this.update();
    }
  }
}
