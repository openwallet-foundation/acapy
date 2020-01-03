import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { NavCardListComponent } from './components/nav-card-list/nav-card-list.component';

const routes: Routes = [
  { path: '', component: NavCardListComponent },
  {
    path: 'connections',
    loadChildren: () => import('./connection/connection.module').then(m => m.ConnectionModule),
  },
  {
    path: 'credentials',
    loadChildren: () => import('./credential/credential.module').then(m => m.CredentialModule),
  },
  {
    path: 'proofs',
    loadChildren: () => import('./proof/proof.module').then(m => m.ProofModule),
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
