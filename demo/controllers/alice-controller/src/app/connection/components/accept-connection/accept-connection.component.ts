import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, FormControl, AsyncValidatorFn, ValidationErrors } from '@angular/forms';
import { Router } from '@angular/router';

import { AgentService } from 'src/app/services/agent.service';

import { map, debounceTime, distinctUntilChanged, filter, tap } from 'rxjs/operators';
import { Observable, timer, BehaviorSubject } from 'rxjs';

function debouncedInvitationValidator(): AsyncValidatorFn {
  return (control: FormControl): Observable<ValidationErrors | null> => {
    return timer(300)
      .pipe(
        map(() => {
          try {
            JSON.parse(control.value);
            return null;
          } catch (error) {
            return { json: error.message };
          }
        })
      );
  };
}

@Component({
  selector: 'app-accept-connection',
  templateUrl: './accept-connection.component.html',
  styleUrls: ['./accept-connection.component.scss']
})
export class AcceptConnectionComponent implements OnInit {
  form: FormGroup;

  invitationUrlError$ = new BehaviorSubject<string>(null);

  constructor(private agentService: AgentService, private fb: FormBuilder, private router: Router) {
    this.form = this.fb.group({
      invitation: [null, Validators.required, debouncedInvitationValidator()],
      invitationUrl: [null, Validators.nullValidator]
    });
  }

  public get invitation(): FormControl {
    return this.form && this.form.get('invitation') as FormControl;
  }

  public get invitationUrl(): FormControl {
    return this.form && this.form.get('invitationUrl') as FormControl;
  }

  ngOnInit() {
    this.invitationUrl.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        tap(() => this.invitationUrlError$.next(null)),
        filter((value: string) => !!value),
        map((value: string) => {
          try {
            const url = new URL(value);
            const invitationParam = url.searchParams.get('c_i');
            if (!invitationParam) {
              throw new Error();
            }

            this.invitation.setValue(JSON.stringify(JSON.parse(atob(invitationParam)), null, 4));
            this.invitation.markAsDirty();
            this.invitation.updateValueAndValidity();
          } catch (error) {
            this.invitationUrlError$.next('Invalid invitation URL');
          }
        }),
      )
      .subscribe();
  }

  onSubmit() {
    if (!this.form.valid) {
      return;
    }
    this.agentService.receiveInvitation(this.invitation.value)
      .pipe(
        map(() => this.router.navigateByUrl('/connections'))
      )
      .subscribe();
  }

}
