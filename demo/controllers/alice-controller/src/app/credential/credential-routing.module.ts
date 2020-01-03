import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { CredentialComponent } from './components/credential/credential.component';
import { CredentialListComponent } from './components/credential-list/credential-list.component';

const routes: Routes = [
  {
    path: '',
    component: CredentialComponent,
    children: [
      { path: '', component: CredentialListComponent }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class CredentialRoutingModule { }
