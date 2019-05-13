import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { ContactComponent } from './info/contact.component';
import { CredFormComponent } from './cred/form.component';
import { HomeComponent } from './home/home.component';
import { IssuerFormComponent } from './issuer/form.component';
import { NotFoundComponent } from './util/not-found.component';
import { SearchComponent } from './search/form.component';
import { TopicFormComponent } from './topic/form.component';

export const ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'home',
    pathMatch: 'full'
  },
  {
    path: 'home',
    component: HomeComponent
  },
  {
    path: 'search',
    redirectTo: '/search/name',
    pathMatch: 'full'
  },
  {
    path: 'search/:filterType',
    component: SearchComponent,
    data: {
      breadcrumb: 'search.breadcrumb'
    }
  },
  {
    path: 'topic/:sourceType/:sourceId',
    data: {
      breadcrumb: 'topic.breadcrumb'
    },
    children: [
      {
        path: '',
        component: TopicFormComponent,
      },
      {
        path: 'cred/:credId',
        data: {
          breadcrumb: 'cred.breadcrumb'
        },
        children: [
          {
            path: '',
            component: CredFormComponent,
          },
          {
            path: 'verify',
            component: CredFormComponent,
            data: {
              breadcrumb: 'cred.verify-breadcrumb',
              verify: true
            }
          }
        ]
      }
    ]
  },
  {
    path: 'topic/:sourceId',
    data: {
      breadcrumb: 'topic.breadcrumb'
    },
    children: [
      {
        path: '',
        component: TopicFormComponent,
      },
      {
        path: 'cred/:credId',
        data: {
          breadcrumb: 'cred.breadcrumb'
        },
        children: [
          {
            path: '',
            component: CredFormComponent,
          },
          {
            path: 'verify',
            component: CredFormComponent,
            data: {
              breadcrumb: 'cred.verify-breadcrumb',
              verify: true
            }
          }
        ]
      }
    ]
  },
  {
    path: 'issuer/:issuerId',
    component: IssuerFormComponent,
    data: {
      breadcrumb: 'issuer.breadcrumb',
    }
  },
  {
    path: 'contact',
    component: ContactComponent,
    data: {
      breadcrumb: 'connect.breadcrumb',
    }
  },
  {
    path: '**',
    component: NotFoundComponent,
    data: {
      breadcrumb: 'not-found.breadcrumb'
    }
  }
];

@NgModule({
  imports: [
    RouterModule.forRoot(ROUTES),
  ],
  exports: [
    RouterModule,
  ]
})
export class AppRoutingModule { }
