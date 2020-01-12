import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { RouterModule } from '@angular/router';

import { ComponentNavComponent } from './components/component-nav/component-nav.component';
import { EmptyListComponent } from './components/empty-list/empty-list.component';

import { ToDatePipe } from './pipes/to-date.pipe';

@NgModule({
  declarations: [ComponentNavComponent, EmptyListComponent, ToDatePipe],
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
    EmptyListComponent,
    ToDatePipe
  ]
})
export class SharedModule { }
