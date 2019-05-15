import { Component, Host } from '@angular/core';
import { AppComponent } from '../app.component';

@Component({
  selector: 'app-footer',
  templateUrl: '../../themes/_active/app-footer/app-footer.component.html',
  styleUrls: ['../../themes/_active/app-footer/app-footer.component.scss']
})
export class AppFooterComponent {

  constructor (
    @Host() public parent: AppComponent
  ) { }

}
