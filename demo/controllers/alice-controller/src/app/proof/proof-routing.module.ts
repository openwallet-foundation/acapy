import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { ProofComponent } from './components/proof/proof.component';
import { ProofListComponent } from './components/proof-list/proof-list.component';

const routes: Routes = [
  {
    path: '',
    component: ProofComponent,
    children: [
      { path: '', component: ProofListComponent }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ProofRoutingModule { }
