import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { LocalizeRouterModule } from 'localize-router';
import { NgbPopoverModule } from '@ng-bootstrap/ng-bootstrap';
import { NgbTooltipModule } from '@ng-bootstrap/ng-bootstrap';
import { AddressComponent } from './address.component';
import { AttributeComponent } from './attribute.component';
import { AttributeListComponent } from './attribute-list.component';
import { BreadcrumbComponent } from './breadcrumb.component';
import { DateFormatPipe } from './date-format.pipe';
import { ErrorMessageComponent } from './error-message.component';
import { LoadingIndicatorComponent } from './loading-indicator.component';
import { PageScrollComponent } from './pagescroll.component';
import { NotFoundComponent } from './not-found.component';
import { NumberShortenPipe } from './number-shorten.pipe';
import { ResolveUrlPipe } from './resolve-url.pipe';
import { ShareLinkComponent } from './share-link.component';
import { WithLangDirective } from './with-lang.directive';

const ROUTES = [];

@NgModule({
  declarations: [
    AddressComponent,
    AttributeComponent,
    AttributeListComponent,
    BreadcrumbComponent,
    DateFormatPipe,
    ErrorMessageComponent,
    LoadingIndicatorComponent,
    PageScrollComponent,
    NotFoundComponent,
    NumberShortenPipe,
    ResolveUrlPipe,
    ShareLinkComponent,
    WithLangDirective,
  ],
  providers: [
  ],
  imports: [
    CommonModule,
    NgbPopoverModule,
    NgbTooltipModule,
    TranslateModule.forChild(),
    RouterModule.forChild(ROUTES),
    LocalizeRouterModule.forChild(ROUTES),
  ],
  exports: [
    AddressComponent,
    AttributeComponent,
    AttributeListComponent,
    BreadcrumbComponent,
    DateFormatPipe,
    ErrorMessageComponent,
    LoadingIndicatorComponent,
    PageScrollComponent,
    NgbPopoverModule,
    NgbTooltipModule,
    NotFoundComponent,
    NumberShortenPipe,
    ResolveUrlPipe,
    ShareLinkComponent,
    WithLangDirective,
  ]
})
export class UtilModule {}

