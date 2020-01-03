import { Component, OnInit } from '@angular/core';

import { AgentService } from 'src/app/services/agent.service';

import { map } from 'rxjs/operators';

@Component({
  selector: 'app-credential-list',
  templateUrl: './credential-list.component.html',
  styleUrls: ['./credential-list.component.scss']
})
export class CredentialListComponent implements OnInit {
  credentials: any[] = [];

  constructor(private agentService: AgentService) { }

  ngOnInit() {
    this.agentService.getCredentials()
      .pipe(
        map((credentials: any[]) => this.credentials = credentials)
      )
      .subscribe();
  }

}
