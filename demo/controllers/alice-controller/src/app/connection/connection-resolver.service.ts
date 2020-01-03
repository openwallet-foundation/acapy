import { Injectable } from '@angular/core';
import { Resolve, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';

import { AgentService } from '../services/agent.service';

import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class ConnectionResolverService implements Resolve<any[]> {

  constructor(private agentService: AgentService) { }

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<any[]> {
    return this.agentService.getConnections()
      .pipe(
        map((connections: any[]) => {
          if (route.routeConfig.path === 'active') {
            return connections.filter((connection: any) => connection.state === 'active' || connection.state === 'request');
          } else if (route.routeConfig.path === 'pending') {
            return connections.filter((connection: any) => connection.state === 'invitation');
          } else {
            return [];
          }
        })
      );
  }
}
