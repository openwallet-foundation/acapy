import { Component, Input } from '@angular/core';

@Component({
  selector: 'loading-indicator',
  templateUrl: '../../themes/_active/util/loading-indicator.component.html'
})
export class LoadingIndicatorComponent {
  @Input() loading: boolean = true;
  @Input() inline: boolean = false;
}
