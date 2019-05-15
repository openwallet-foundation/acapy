import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import 'rxjs/add/operator/filter';

const ROUTE_DATA_BREADCRUMB: string = 'breadcrumb';
const PRIMARY_OUTLET: string = 'primary';

@Component({
  selector: 'app-breadcrumb',
  templateUrl: '../../themes/_active/util/breadcrumb.component.html',
  styleUrls: ['../../themes/_active/util/breadcrumb.component.scss']
})
export class BreadcrumbComponent implements OnInit, OnDestroy {
  public breadcrumbs: any[] = [];
  private _sub;
  private _linkCurrent = false;

  constructor (
    private _router: Router,
    private _route: ActivatedRoute
  ) { }

  ngOnInit() {
    this.update();

    this._sub = this._router.events
      .filter(event => event instanceof NavigationEnd)
      .subscribe(this.update.bind(this));
  }

  ngOnDestroy() {
    if(this._sub) {
      this._sub.unsubscribe();
      this._sub = null;
    }
  }

  update(evt?) {
    let crumbs = this.resolveBreadcrumbs(this._route.root, '/', '');
    if(crumbs.length) {
      crumbs[crumbs.length - 1].current = true;
      if(! this._linkCurrent)
        crumbs[crumbs.length - 1].url = null;
    }
    this.breadcrumbs = crumbs;
  }

  resolveBreadcrumbs(route, urlPrefix : string, prevName : string) {
    let ret = [];
    let children = route.children;
    if(children) {
      children.forEach(child => {

        // Verify this is the primary route
        if (child.outlet !== PRIMARY_OUTLET) {
          return;
        }

        //get the route's URL segment
        let routeURL: string = urlPrefix + child.snapshot.url
            .map(segment => segment.path)
            .join('/');

        // Verify the custom data property "breadcrumb" is specified on the route
        if (child.snapshot.data.hasOwnProperty(ROUTE_DATA_BREADCRUMB)) {
          let bcName = child.snapshot.data[ROUTE_DATA_BREADCRUMB];
          if(bcName !== null && bcName !== '' && bcName !== prevName) {
            ret.push({
              label: child.snapshot.data[ROUTE_DATA_BREADCRUMB],
              url: routeURL
            });
          }
          prevName = bcName;
        }

        ret = ret.concat(this.resolveBreadcrumbs(child, routeURL + '/', prevName));
      });
    }
    return ret;
  }
}
