import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { RouterModule } from '@angular/router';

import { ComponentNavComponent } from './components/component-nav/component-nav.component';
import { EmptyListComponent } from './components/empty-list/empty-list.component';

@NgModule({
  declarations: [ComponentNavComponent, EmptyListComponent],
  imports: [
    CommonModule,
    HttpClientModule,
    RouterModule
  ],
  exports: [
    CommonModule,
    HttpClientModule,
    RouterModule,
    // Components
    ComponentNavComponent,
    EmptyListComponent
  ]
})
export class SharedModule { }
