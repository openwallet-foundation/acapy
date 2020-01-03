import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { SharedModule } from '../shared/shared.module';

import { ConnectionRoutingModule } from './connection-routing.module';
import { ConnectionComponent } from './components/connection/connection.component';
import { ConnectionListComponent } from './components/connection-list/connection-list.component';
import { NewConnectionComponent } from './components/new-connection/new-connection.component';
import { AcceptConnectionComponent } from './components/accept-connection/accept-connection.component';
import { ConnectionCardComponent } from './components/connection-card/connection-card.component';

@NgModule({
  declarations: [ConnectionComponent, ConnectionListComponent, NewConnectionComponent, AcceptConnectionComponent, ConnectionCardComponent],
  imports: [
    CommonModule,
    SharedModule,
    FormsModule,
    ReactiveFormsModule,
    ConnectionRoutingModule
  ]
})
export class ConnectionModule { }
