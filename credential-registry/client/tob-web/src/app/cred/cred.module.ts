import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { LocalizeRouterModule } from 'localize-router';
import { CredFormComponent } from './form.component';
import { CredListComponent } from './list.component';
import { CredTypeListComponent } from './type-list.component';
import { IssuerFormComponent } from '../issuer/form.component';
import { NamePanelComponent } from './name-panel.component';
import { RelatedCredsComponent } from './related-list.component';
import { TimelineCredComponent } from './timeline-cred.component';
import { TimelineFormatterService } from './timeline-formatter.service';
import { TimelineViewComponent } from '../timeline/view.component';
import { CredSetTimelineComponent } from './timeline.component';
import { UtilModule } from '../util/util.module';


const ROUTES = [];

@NgModule({
  declarations: [
    CredFormComponent,
    CredListComponent,
    CredTypeListComponent,
    IssuerFormComponent,
    NamePanelComponent,
    RelatedCredsComponent,
    CredSetTimelineComponent,
    TimelineCredComponent,
    TimelineViewComponent,
  ],
  entryComponents: [
    TimelineCredComponent,
  ],
  providers: [
    TimelineFormatterService,
  ],
  imports: [
    CommonModule,
    FormsModule,
    TranslateModule.forChild(),
    RouterModule.forChild(ROUTES),
    LocalizeRouterModule.forChild(ROUTES),
    UtilModule,
  ],
  exports: [
    CredFormComponent,
    CredListComponent,
    CredTypeListComponent,
    IssuerFormComponent,
    NamePanelComponent,
    RelatedCredsComponent,
    CredSetTimelineComponent,
    TimelineCredComponent,
    TimelineViewComponent,
  ]
})
export class CredModule {}

