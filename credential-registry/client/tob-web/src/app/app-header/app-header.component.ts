import { Component, Host } from '@angular/core';
import { AppComponent } from '../app.component';

@Component({
  selector: 'app-header',
  templateUrl: '../../themes/_active/app-header/app-header.component.html',
  styleUrls: ['../../themes/_active/app-header/app-header.component.scss']
})
export class AppHeaderComponent {
  navCollapsed: boolean = true;

  constructor (
    @Host() public parent: AppComponent
  ) { }

  toggleNavCollapsed(evt?) {
    this.navCollapsed = ! this.navCollapsed;
  }

  moveFocus(evt, id) {
    evt.preventDefault();
    let main = document.getElementById(id);
    if(main) {
      main.focus();
      location.hash = id;
    }
  }
}
