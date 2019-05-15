import { ComponentFactoryResolver, Injectable, Injector } from '@angular/core';
import { Model } from '../data-types';
import { LocalizeRouterService } from 'localize-router';
import { TimelineCredComponent } from './timeline-cred.component';

@Injectable()
export class TimelineFormatterService {

  constructor(
    private _resolver: ComponentFactoryResolver,
    private _injector: Injector,
    private _localize: LocalizeRouterService,
  ) {
  }

  getCredentialUrl(cred: Model.Credential) {
    let parts = [...cred.topic.link, '/cred/', cred.id];
    let url = <string[]>this._localize.translateRoute(parts);
    return url.join('');
  }

  renderCredential(cred: Model.Credential) {
    const factory = this._resolver.resolveComponentFactory(TimelineCredComponent);
    const component = factory.create(this._injector);
    component.instance.credential = cred;
    component.changeDetectorRef.detectChanges();
    let htmlContent = component.location.nativeElement.outerHTML;
    component.destroy();
    return htmlContent;
  }

  getCredentialSlot(cred: Model.Credential) {
    let cls = 'slot-primary';
    if(cred.inactive)
      cls = 'slot-secondary';
    else if(cred.latest)
      cls = 'slot-success';
    return {
      id: `cred-${cred.id}`,
      groups: [],
      htmlContent: this.renderCredential(cred),
      start: cred.effective_date,
      end: cred.revoked_date,
      classNames: [cls],
      url: this.getCredentialUrl(cred),
    };
  }

}
