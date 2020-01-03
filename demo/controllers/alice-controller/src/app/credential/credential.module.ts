import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { SharedModule } from '../shared/shared.module';

import { CredentialRoutingModule } from './credential-routing.module';
import { CredentialComponent } from './components/credential/credential.component';
import { CredentialListComponent } from './components/credential-list/credential-list.component';
import { CredentialCardComponent } from './components/credential-card/credential-card.component';

@NgModule({
  declarations: [CredentialComponent, CredentialListComponent, CredentialCardComponent],
  imports: [
    CommonModule,
    SharedModule,
    CredentialRoutingModule
  ]
})
export class CredentialModule { }
