import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { SharedModule } from '../shared/shared.module';

import { ProofRoutingModule } from './proof-routing.module';
import { ProofComponent } from './components/proof/proof.component';
import { ProofListComponent } from './components/proof-list/proof-list.component';
import { ProofCardComponent } from './components/proof-card/proof-card.component';

@NgModule({
  declarations: [ProofComponent, ProofListComponent, ProofCardComponent],
  imports: [
    CommonModule,
    SharedModule,
    ProofRoutingModule
  ]
})
export class ProofModule { }
