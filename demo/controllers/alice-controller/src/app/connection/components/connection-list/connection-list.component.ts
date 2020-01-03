import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { AgentService } from 'src/app/services/agent.service';

import { map, filter } from 'rxjs/operators';

@Component({
  selector: 'app-connection-list',
  templateUrl: './connection-list.component.html',
  styleUrls: ['./connection-list.component.scss']
})
export class ConnectionListComponent implements OnInit {
  connections: any[] = [];

  constructor(private agentService: AgentService, private route: ActivatedRoute) { }

  ngOnInit() {
    this.route.data
      .pipe(
        map((data: { connections: any[] }) => this.connections = data.connections || [])
      )
      .subscribe();
  }

  onRemoveConnection(connection: any) {
    this.agentService.removeConnection(connection.connection_id)
      .pipe(
        filter((connectionId: string) => !!connectionId),
        map((connectionId: string) =>
          this.connections = this.connections.filter((conn: any) => conn.connection_id !== connectionId))
      )
      .subscribe();
  }

}
