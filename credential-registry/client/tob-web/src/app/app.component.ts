import { Component, ElementRef, OnDestroy, OnInit } from '@angular/core';
import { LocationStrategy } from '@angular/common';
import { Title, Meta } from '@angular/platform-browser';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { LocalizeRouterService } from 'localize-router';
import { GeneralDataService } from './general-data.service';
import { LangChangeEvent, TranslateService } from '@ngx-translate/core';
import { Subscription } from 'rxjs/Subscription';
import { mergeMap, map } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  templateUrl: '../themes/_active/app/app.component.html',
  styleUrls: ['../themes/_active/app/app.component.scss']
})
export class AppComponent implements OnInit, OnDestroy {
  currentLang: string;
  inited = false;
  // to be moved into external JSON loaded by localize-router
  supportedLanguages = [
    {
      name: 'en',
      label: 'English'
    },
    {
      name: 'fr',
      label: 'Français'
    }
  ];
  altLang: string;
  altLangLabel: string;
  defaultTitleLabel = 'app.title';
  showTitlePrefix: boolean = true;
  titlePrefix = 'app.title-prefix';
  private _titleLabel;
  private _titleText = '';
  private _titlePrefixText;
  private _onFetchTitle: Subscription;
  private _onLangChange: Subscription;
  private _isPopState: boolean;
  private _currentRecord: any;
  private _prevRoute: string;
  private _metaDefaults = null;

  constructor(
    public _el: ElementRef,
    private _dataService: GeneralDataService,
    private _localize: LocalizeRouterService,
    private _locStrat: LocationStrategy,
    private _meta: Meta,
    private _route: ActivatedRoute,
    private _router: Router,
    private _titleService: Title,
    public translate: TranslateService,
  ) {}

  ngOnInit() {
  	this._locStrat.onPopState(() => {
      this._isPopState = true;
    });

    this._dataService.onCurrentResult((result) => {
      if(result && result.loaded) {
        this._currentRecord = result.data;
      } else {
        this._currentRecord = null;
        if(result && result.notFound) {
          console.log('not found!');
        }
      }
      this.updateTitle();
    });

    let scrollWindow = function(top, now?) {
      if(! now) {
        setTimeout(() => scrollWindow(top, true), 50);
        return;
      }
      try {
        window.scrollTo({top: top || 0, left: 0, behavior: 'smooth'});
      } catch(e) {
        window.scrollTo(0, top || 0);
      }
    };

    this._router.events
      .filter((event) => event instanceof NavigationEnd)
      .pipe(map(() => this._route))
      .pipe(map((route) => {
        while (route.firstChild) route = route.firstChild;
        return route;
      }))
      .filter((route) => route.outlet === 'primary')
      .subscribe((route) => {
        let data = route.snapshot.data;
        let fragment = route.snapshot.fragment;
        let routePath = route.snapshot.routeConfig.path;
        if (!this._isPopState) {
          // scroll to page top only when navigating to a new page (not via history state)
          // skip when fragment (anchor name) is set
          let outer = null;
          if(fragment) {
            outer = document.getElementById(fragment);
          }
          if(! outer) {
            outer = document.getElementById('primaryOutlet');
          }
          if(! outer) {
            outer = document.getElementsByTagName('main')[0];
          }
          let top = outer && (<HTMLElement>outer).offsetTop;
          if(top) {
            if(window.scrollY > top) scrollWindow(top);
          } else {
            scrollWindow(0);
          }
        }
        this._isPopState = false;
        this._currentRecord = null;
        this._prevRoute = routePath;

        let title = data['title'] || data['breadcrumb'];
        this.titleLabel = title;
      });

    // Initialize fallback and initial language
    // NOTE - currently superceded by localize-router
    // this.translate.setDefaultLang(this.supportedLanguages[0]);
    // this.translate.use(this.guessLanguage());

    this._onLangChange = this.translate.onLangChange.subscribe((event: LangChangeEvent) => {
      this.onUpdateLanguage(event.lang);
    });
    if(this.translate.currentLang) {
      // may already be initialized by localize-router
      this.onUpdateLanguage(this.translate.currentLang);
    }
  }

  ngOnDestroy() {
    if (this._onLangChange !== undefined) {
      this._onLangChange.unsubscribe();
    }
    if (this._onFetchTitle !== undefined) {
      this._onFetchTitle.unsubscribe();
    }
  }

  onUpdateLanguage(lang) {
    if(lang && lang !== this.currentLang) {
      console.log('Language:', lang);
      this.currentLang = lang;
      // need to add some functionality to localize-router to handle this properly
      let alt = this.altLanguageInfo();
      this.altLang = alt ? alt.name : 'en';
      this.altLangLabel = alt ? alt.label : '';
      // set the lang attribute on the html element
      this._el.nativeElement.parentElement.parentElement.setAttribute('lang', lang);
      this.fetchTitle();
      this.checkInit();
    }
  }

  checkInit() {
    if(this.currentLang) {
      this.inited = true;
    }
  }

  altLanguageInfo() {
    for(let lang of this.supportedLanguages) {
      if(lang.name !== this.currentLang)
        return lang;
    }
  }

  public changeLanguage(lang: string) {
    this._localize.changeLanguage(lang);
  }

  public switchLanguage(evt) {
    if(this.altLang) {
      this._localize.changeLanguage(this.altLang);
    }
    if(evt) {
      evt.preventDefault();
    }
  }

  /**
   * Returns the current lang for the application
   * using the existing base path
   * or the browser lang if there is no base path
   * @returns {string}
   */
  public guessLanguage(): string | null {
    let ret = this.supportedLanguages[0]['name'];
    if(typeof window !== 'undefined' && typeof window.navigator !== 'undefined') {
      let lang = (window.navigator['languages'] ? window.navigator['languages'][0] : null)
        || window.navigator.language
        || window.navigator['browserLanguage']
        || window.navigator['userLanguage']
        || '';
      if(lang.indexOf('-') !== -1) {
        lang = lang.split('-')[0];
      }
      if(lang.indexOf('_') !== -1) {
        lang = lang.split('_')[0];
      }
      lang = lang.toLowerCase();
      for(let check of this.supportedLanguages) {
        if(check.name === lang) {
          ret = lang;
          break;
        }
      }
    }
    return ret;
  }

  get titleLabel(): string {
    return this._titleLabel || this.defaultTitleLabel;
  }

  set titleLabel(newLabel: string) {
    this._titleLabel = newLabel;
    this.showTitlePrefix = !! newLabel;
    this.fetchTitle();
  }

  public fetchTitle() {
    if (this._onFetchTitle !== undefined) {
      this._onFetchTitle.unsubscribe();
    }
    let lbl = this.titleLabel;
    this._onFetchTitle = this.translate.stream(lbl).subscribe((res: string) => {
      this._titleText = res;
      if(this.titlePrefix) {
        let pfx = this.translate.get(this.titlePrefix);
        this._titlePrefixText = pfx['value'];
      } else {
        this._titlePrefixText = '';
      }
      this.updateTitle();
    });
  }

  public updateTitle() {
    let title = '';
    if(this.showTitlePrefix && this._titlePrefixText) {
      title = this._titlePrefixText;
    }
    if(this._titleText)
      title += this._titleText;
    if(title && this._currentRecord) {
      let recordTitle = this._currentRecord.pageTitle;
      if(recordTitle) {
        title += ': ' + recordTitle;
      }
    }
    if(title) {
      this.setTitle(title);
      this.updateMeta(title);
    }
  }

  public setTitle(newTitle: string) {
    this._titleService.setTitle(newTitle);
  }

  public updateMeta(title) {
    if(! this._metaDefaults) {
      let defaults = {};
      let initFrom = ['og:title', 'og:type', 'og:description', 'og:url'];
      for(let attr of initFrom) {
        let meta = this._meta.getTag(`property="${attr}"`);
        if(meta) defaults[attr] = meta.getAttribute('content');
      };
      this._metaDefaults = defaults;
    }
    let tags = Object.assign({}, this._metaDefaults);
    let route = this._route;
    while(route.firstChild) {
      route = route.firstChild;
    }
    if(route && route.routeConfig && route.routeConfig.path !== 'home') {
      tags['og:url'] = location.href;
      if(this._currentRecord) {
        let recLink = this._currentRecord.link;
        if(recLink) {
          // let linkParts = <string[]>this._localize.translateRoute(recLink);
          let linkStr = recLink.join('').replace(/^\/(en|fr)/, '');
          tags['og:url'] = location.origin + linkStr;
        }
      }
      if(title) {
        tags['og:title'] = title;
        tags['og:type'] = 'article';
      }
    }
    for(let attr in tags) {
      this._meta.updateTag({ property: attr, content: tags[attr] }, `property="${attr}"`);
    }
  }

  get showDebugMsg() {
    return this._dataService.showDebugMsg;
  }
}

