import { Component, Input, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { LocalizeRouterService } from 'localize-router';

function joinPath(path) {
  if(typeof path === 'string')
    return path;
  return path.join('/');
}

@Component({
  selector: 'app-not-found',
  templateUrl: '../../themes/_active/util/not-found.component.html'
})
export class NotFoundComponent implements OnInit {
  @Input() nested: boolean = false;

  constructor(
    private _router: Router,
    private _route: ActivatedRoute,
    private _localize: LocalizeRouterService
  ) {
  }

  ngOnInit() {
    let url = this._route.snapshot.url.map(segment => segment.path);
    if(url.length) {
      let pfx = false;
      if(url[0].length == 2) { // language code
        url.shift();
        pfx = true;
      }
      let translated = <string[]>this._localize.translateRoute(['/', ...url]);
      if(translated.length && (! pfx || joinPath(url) != joinPath(translated.slice(1)))) {
        console.log('redirect:', translated);
        this._router.navigate(translated);
      }
    }
  }
}
