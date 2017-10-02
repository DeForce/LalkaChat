import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { CoreModule } from 'app/core';
import { SharedModule } from 'app/shared';

@NgModule({
  imports: [
    BrowserModule,
    SharedModule,
    CoreModule
  ],
  bootstrap: [CoreModule.bootstrap],
})
export class AppModule { }
