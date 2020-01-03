import { Component, OnInit } from '@angular/core';

import { AgentService } from 'src/app/services/agent.service';

import { map } from 'rxjs/operators';

@Component({
  selector: 'app-proof-list',
  templateUrl: './proof-list.component.html',
  styleUrls: ['./proof-list.component.scss']
})
export class ProofListComponent implements OnInit {
  proofs: any[] = [];

  constructor(private agentService: AgentService) { }

  ngOnInit() {
    this.agentService.getProofs()
      .pipe(
        map((proofs: any[]) => this.proofs = proofs)
      )
      .subscribe();
  }

}
