import { Injectable } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { BehaviorSubject, concat, of, from, Observable, Observer, Subscription } from 'rxjs';
import { catchError, map, mergeMap, switchMap, shareReplay } from 'rxjs/operators';
import { _throw } from 'rxjs/observable/throw';
import { environment } from '../environments/environment';
import { Fetch, Filter, Model } from './data-types';


@Injectable()
export class GeneralDataService {

  public apiUrl = environment.API_URL;
  private _quickLoaded = false;
  private _orgData : {[key: string]: any} = {};
  private _recordCounts : {[key: string]: number} = {};
  private _currentResultSubj = new BehaviorSubject<Fetch.BaseResult<any>>(null);
  private _loaderSub: Subscription = null;
  private _defaultTopicType = 'registration';
  private _showDebugMsg = false;
  private _credTypeLang =  {};

  constructor(
    private _http: HttpClient,
    private _translate: TranslateService,
  ) {
  }

  get language() {
    return this._translate.currentLang;
  }

  get showDebugMsg() {
    return this._showDebugMsg;
  }

  getRequestUrl(path: string) : string {
    if(typeof path === 'string' && path.match(/^(\/\/|\w+:\/\/)\w/)) {
      // absolute URL
      return path;
    }
    let root = (<any>window).testApiUrl || this.apiUrl;

    if(root) {
      if(! root.endsWith('/')) root += '/';
      return root + path;
    }
  }

  get defaultTopicType(): string {
    return this._defaultTopicType;
  }

  loadJson(url, params?: HttpParams) : Observable<Object> {
    return this._http.get(url, {params})
      .pipe(catchError(error => {
        console.error("JSON load error", error);
        return _throw(error);
      }));
  }

  postJson(url, payload, params?: HttpParams) : Observable<Object> {
    let headers = {'Content-Type': 'application/json'};
    return this._http.post(url, JSON.stringify(payload), {headers, params})
      .pipe(catchError(error => {
        console.error("JSON load error", error);
        return _throw(error);
      }));
  }

  postParams(url, params: {[key: string]: string}|HttpParams) : Observable<Object> {
    let body = this.makeHttpParams(params);
    return this._http.post(url, body)
      .pipe(catchError(error => {
        console.error("JSON load error", error);
        return _throw(error);
      }));
  }

  loadFromApi(path: string, params?: HttpParams) : Observable<Object> {
    let url = this.getRequestUrl(path);
    if(url) {
      return this.loadJson(url, params);
    }
  }

  quickLoad(force?) {
    return new Promise((resolve, reject) => {
      if(this._quickLoaded && !force) {
        resolve(1);
        return;
      }
      let baseurl = this.getRequestUrl('');
      if(! baseurl) {
        reject("Base URL not defined");
        return;
      }
      let req = this._http.get(baseurl + 'quickload')
        .pipe(catchError(error => {
          console.error(error);
          return _throw(error);
        }));
      req.subscribe((data: any) => {
        if(data.counts) {
          for (let k in data.counts) {
            this._recordCounts[k] = parseInt(data.counts[k]);
          }
        }
        if(data.credential_counts) {
          for (let k in data.credential_counts) {
            this._recordCounts[k] = parseInt(data.credential_counts[k]);
          }
        }
        if(data.records) {
          for (let k in data.records) {
            this._orgData[k] = data.records[k];
          }
        }
        if(data.demo) {
          this._showDebugMsg = true;
        }
        this._quickLoaded = true;
        resolve(1);
      }, err => {
        reject(err);
      });
    });
  }

  getRecordCount (type) {
    return this._recordCounts[type] || 0;
  }

  autocomplete (term) : Observable<Object> {
    if(term === '' || typeof(term) !== 'string') {
      return from([]);
    }
    let params = new HttpParams().set('q', term);
    return this.loadFromApi('search/autocomplete', params)
      .pipe(map(response => {
        let ret = [];
        for(let row of response['results']) {
          let found = null;
          for(let name of row.names) {
            if(~ name.text.toLowerCase().indexOf(term.toLowerCase())) {
              found = name.text;
              break;
            } else if(found === null) {
              found = name.text;
            }
          }
          if(found !== null) {
            ret.push({id: row.id, term: found});
          }
        }
        return ret;
      }));
  }

  makeHttpParams(query?: { [key: string ]: string } | HttpParams) {
    let httpParams: HttpParams;
    if(query instanceof HttpParams) {
      httpParams = query;
    } else {
      httpParams = new HttpParams();
      if(query) {
        for(let k in query) {
          httpParams = httpParams.set(k, query[k]);
        }
      }
    }
    return httpParams;
  }

  fixRecordId (id: number | string) {
    if(typeof id === 'number')
      id = ''+id;
    return id;
  }

  loadRecord <T>(
      fetch: Fetch.DataLoader<T>,
      id: string | number,
      params?: { [key: string ]: any }) {
    if(! params) params = {};
    let path = params.path || fetch.request.getRecordPath(
      this.fixRecordId(id), this.fixRecordId(params.childId), params.extPath);
    return this.loadData(fetch, path, params);
  }

  loadList <T>(fetch: Fetch.ListLoader<T>, params?: { [key: string ]: any }) {
    if(! params) params = {};
    let path = params.path || fetch.request.getListPath(params.parentId, params.extPath);
    return this.loadData(fetch, path, params);
  }

  loadAll <M extends Model.BaseModel>(
      ctor: Model.ModelCtor<M>): Promise<M[]> {
    let loader = new Fetch.ModelListLoader<M>(ctor);
    let allRows: M[] = [];
    return new Promise((resolve, fail) => {
      loader.stream.subscribe(result => {
        // FIXME - implement pagination
        if(result.loaded) {
          allRows = allRows.concat(result.data);
          resolve(allRows);
        }
      });
      this.loadList(loader);
    });
  }

  loadData <T, R extends Fetch.BaseResult<T>>(fetch: Fetch.BaseLoader<T,R>, path: string, params?: { [key: string ]: any }) {
    if(! params) params = {};
    if(! path)
      // fetch.loadNotFound
      fetch.loadError("Undefined resource path");
    else {
      let httpParams = this.makeHttpParams(params.query);
      let url = this.getRequestUrl(path);
      if(params.primary) {
        if(this._loaderSub)
          this._loaderSub.unsubscribe();
        this._loaderSub = fetch.stream.subscribe((result) => {
          this.setCurrentResult(result);
        });
      }
      fetch.loadFrom(this.loadJson(url, httpParams), {url: url});
    }
  }

  public loadFacetOptions(data) {
    let fields = data.info && data.info.facets && data.info.facets.fields || {};
    let options = {
      credential_type_id: [],
      issuer_id: [],
      'category:entity_type': [],
    };
    if(fields) {
      for(let optname in fields) {
        for(let optitem of fields[optname]) {
          if(! optitem.count)
            // skip facets with no results
            continue;
          let optidx = optname;
          let optval: Filter.Option = {label: optitem.text, value: optitem.value, count: optitem.count};
          if(optname == 'category') {
            let optparts = optitem.value.split('::', 2);
            if(optparts.length == 2) {
              optidx = optname + ':' + optparts[0];
              let lblkey = `category.${optparts[0]}.${optparts[1]}`;
              let label = this._translate.instant(lblkey);
              if(label === lblkey || label === `??${lblkey}??`)
                label = optparts[1];
              optval = {
                label,
                value: optparts[1],
                count: optitem.count,
              };
            }
          }
          if(optidx in options) {
            options[optidx].push(optval);
          }
        }
      }
    }
    for(let name in options) {
      options[name].sort((a,b) => a.label.localeCompare(b.label));
    }
    return options;
  }

  onCurrentResult(sub): Subscription {
    return this._currentResultSubj.subscribe(sub);
  }

  setCurrentResult(result: Fetch.BaseResult<any>) {
    this._currentResultSubj.next(result);
  }

  deleteRecord (mod: string, id: string) {
    return new Promise(resolve => {
      let baseurl = this.getRequestUrl(`${mod}/${id}/delete`);
      let req = this._http.post(baseurl, {params: {id}})
        .pipe(catchError(error => {
          console.error(error);
          resolve(null);
          return _throw(error);
        }));
      req.subscribe(data => {
        console.log('delete result', data);
        resolve(data);
      });
    });
  }

  loadCredentialTypeLanguage(credTypeId) {
    return Observable.create((observer: Observer<any>) => {
      let url = this.getRequestUrl(`credentialtype/${credTypeId}/language`);
      this.loadJson(url).subscribe(
        data => { observer.next(data); observer.complete(); },
        err  => { observer.error(err); }
      );
    });
  }

  getCredentialTypeLanguage(id) {
    if(! id) {
      return of(null);
    }
    if(! this._credTypeLang[id]) {
      this._credTypeLang[id] = //concat(
        this.loadCredentialTypeLanguage(id).pipe(shareReplay(1)); /*,
        this._translate.onLangChange.pipe(
          switchMap((event) => null, (outer, inner) => { console.log(outer, inner); return outer; })
        )*/
      //);
    }
    return this._credTypeLang[id];
  }

  getCredentialTypeLanguageKey(credTypeId, key) {
    return this.getCredentialTypeLanguage(credTypeId).pipe(map(data => (data && data[key])));
  }

  preloadCredentialTypeLanguage(...ids) {
    return new Promise(resolve => {
      let result = Promise.resolve(null);
      if(ids) {
        for(let i = 0; i < ids.length; i ++) {
          result = result.then(this.getCredentialTypeLanguage(ids[i]));
        }
      }
      result.then(() => resolve(null));
    });
  }

  translateClaimDescription(credTypeId, claimName, defVal?) {
    let credLang = this.getCredentialTypeLanguageKey(credTypeId, 'claim_descriptions');
    return credLang.then(values => {
      let lang = this.language;
      let ret = undefined;
      if(lang in values) {
        ret = values[lang][claimName];
      }
      if(ret === undefined)
        ret = defVal;
      return ret;
    });
  }

  translateClaimLabel(credTypeId, claimName, defVal?) {
    let credLang = this.getCredentialTypeLanguageKey(credTypeId, 'claim_labels');
    return credLang.then(values => {
      let lang = this.language;
      let ret = undefined;
      if(lang in values) {
        ret = values[lang][claimName];
      }
      if(ret === undefined)
        ret = defVal;
      return ret;
    });
  }

  translateCategoryLabel(credTypeId, catType, catValue) {
    let credLang = this.getCredentialTypeLanguageKey(credTypeId, 'category_labels');
    let lbl = `category.${catType}.${catValue}`;
    return credLang.pipe(
      map(values => {
        let lang = this.language;
        let ret = undefined;
        if(values && lang in values) {
          let labels = values[lang];
          if(labels && catType in labels) {
            ret = labels[catType][catValue];
          }
        }
        return ret;
      }),
      mergeMap(val => {
        if(val === undefined)
          return this._translate.stream(lbl).pipe(map(
            lbl => (! lbl || lbl.substring(0, 2) == '??') ? catValue : lbl
          ));
        return of(val);
      })
    );
  }
}
