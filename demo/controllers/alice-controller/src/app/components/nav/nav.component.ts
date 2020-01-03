import { Component, OnInit } from '@angular/core';

import { AgentService } from 'src/app/services/agent.service';
import { AgentStatus } from 'src/app/enums/agent-status.enum';

import { map } from 'rxjs/operators';

@Component({
  selector: 'app-nav',
  templateUrl: './nav.component.html',
  styleUrls: ['./nav.component.scss']
})
export class NavComponent implements OnInit {
  agentStatus = AgentStatus;
  status = this.agentStatus.Loading;

  constructor(private agentService: AgentService) { }

  ngOnInit() {
    this.agentService.getStatus()
      .pipe(
        map((status) => this.status = status)
      )
      .subscribe();
  }

}
