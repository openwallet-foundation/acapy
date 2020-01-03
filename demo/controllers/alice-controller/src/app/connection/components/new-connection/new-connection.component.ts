import { Component, OnInit } from '@angular/core';

import { AgentService } from 'src/app/services/agent.service';
import { filter, map } from 'rxjs/operators';

@Component({
  selector: 'app-new-connection',
  templateUrl: './new-connection.component.html',
  styleUrls: ['./new-connection.component.scss']
})
export class NewConnectionComponent implements OnInit {
  public invitation: any;
  public invitationObject = '';
  public invitationUrl = '';

  constructor(private agentService: AgentService) { }

  ngOnInit() {
  }

  copy(el: HTMLInputElement | HTMLTextAreaElement) {
    el.select();
    document.execCommand('copy');
  }

  onSubmit() {
    this.agentService.createInvitation()
      .pipe(
        filter((invitation: any) => !!invitation),
        map((invitation: any) => {
          this.invitation = invitation;
          this.invitationObject = this.invitation && JSON.stringify(this.invitation.invitation, null, 4) || '';
          this.invitationUrl = this.invitation && this.invitation.invitation_url || '';
        })
      )
      .subscribe();
  }

}
