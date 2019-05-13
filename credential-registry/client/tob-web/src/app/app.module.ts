import { BrowserModule } from '@angular/platform-browser';
import { Location } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { NgModule, APP_INITIALIZER } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Routes } from '@angular/router';

import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
import {
  TranslateModule, TranslateLoader, TranslateService,
  MissingTranslationHandler, MissingTranslationHandlerParams
  } from '@ngx-translate/core';
import {
  LocalizeParser, LocalizeRouterModule, LocalizeRouterSettings, ALWAYS_SET_PREFIX
  } from 'localize-router';
import { ILocalizeRouterParserConfig } from 'localize-router-http-loader';
import { Observable, from } from 'rxjs';

import { AppRoutingModule, ROUTES } from './app-routing.module';
import { AppComponent } from './app.component';
import { AppConfigService } from './app-config.service';
import { AppHeaderComponent } from './app-header/app-header.component';
import { AppFooterComponent } from './app-footer/app-footer.component';
import { ContactComponent } from './info/contact.component';
import { GeneralDataService } from './general-data.service';
import { HomeComponent } from './home/home.component';

import { CredModule } from './cred/cred.module';
import { SearchModule } from './search/search.module';
import { TopicModule } from './topic/topic.module';
import { UtilModule } from './util/util.module';

import { environment } from '../environments/environment';

const ROUTE_PREFIX : string = 'ROUTES.';

export const appInitializerFn = (appConfig: AppConfigService) => {
  return () => {
    return appConfig.loadFromPromise(
      import(/* webpackMode: "eager" */ `../themes/_active/assets/config.json`));
  };
};

export class WebpackTranslateLoader implements TranslateLoader {
  getTranslation(lang: string): Observable<any> {
    return from(
      import(/* webpackMode: "eager" */ `../themes/_active/assets/i18n/${lang}.json`));
  }
}
export class WebpackLocalizeRouterLoader extends LocalizeParser {
  load(routes: Routes): Promise<any> {
    return new Promise((resolve) => {
      import(/* webpackMode: "eager" */ `../themes/_active/assets/locales.json`)
        .then(data => {
            let config = <ILocalizeRouterParserConfig><any>data;
            this.locales = config.locales;
            this.prefix = config.prefix || '';
            this.init(routes).then(resolve);
          }
        );
    });
  }
}
export class MyMissingTranslationHandler implements MissingTranslationHandler {
  handle(params: MissingTranslationHandlerParams) {
    // params: {key, translateService}
    // handle missing route translations
    if(params.key.substring(0, ROUTE_PREFIX.length) === ROUTE_PREFIX) {
      return params.key.substring(ROUTE_PREFIX.length);
    }
    // highlight missing translation strings in development mode
    if(! environment.production && ! ~params.key.indexOf('??')) {
      console.warn("missing translation: " + params.key);
      // return '??' + params.key + '??';
    }
  }
}


@NgModule({
  declarations: [
    AppComponent,
    AppHeaderComponent,
    AppFooterComponent,
    ContactComponent,
    HomeComponent,
  ],
  imports: [
    BrowserModule,
    FormsModule,
    HttpClientModule,
    AppRoutingModule,
    CredModule,
    SearchModule,
    TopicModule,
    TranslateModule.forRoot({
      loader: {
        provide: TranslateLoader,
        useClass: WebpackTranslateLoader
      }
    }),
    LocalizeRouterModule.forRoot(ROUTES, {
      parser: {
        provide: LocalizeParser,
        useClass: WebpackLocalizeRouterLoader,
        deps: [TranslateService, Location, LocalizeRouterSettings]
      }
    }),
    NgbModule.forRoot(),
    UtilModule,
  ],
  exports: [
    CredModule,
    SearchModule,
    TopicModule,
    TranslateModule,
    UtilModule,
  ],
  providers: [
    AppConfigService,
    {
      provide: APP_INITIALIZER,
      useFactory: appInitializerFn,
      multi: true,
      deps: [AppConfigService]
    },
    GeneralDataService,
    {provide: MissingTranslationHandler, useClass: MyMissingTranslationHandler},
    {provide: ALWAYS_SET_PREFIX, useValue: true},
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }

