import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { ConnectionComponent } from './components/connection/connection.component';
import { ConnectionListComponent } from './components/connection-list/connection-list.component';
import { NewConnectionComponent } from './components/new-connection/new-connection.component';
import { AcceptConnectionComponent } from './components/accept-connection/accept-connection.component';

import { ConnectionResolverService } from './connection-resolver.service';

const routes: Routes = [
  {
    path: '',
    component: ConnectionComponent,
    children: [
      { path: 'active', component: ConnectionListComponent, resolve: { connections: ConnectionResolverService } },
      { path: 'pending', component: ConnectionListComponent, resolve: { connections: ConnectionResolverService } },
      { path: 'new', component: NewConnectionComponent },
      { path: 'accept', component: AcceptConnectionComponent },
      { path: '', redirectTo: 'active' }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ConnectionRoutingModule { }
