import { NgModule, Type } from '@angular/core';
import { CommonModule } from '@angular/common';

import { MessageComponent } from './message';
import { RootComponent } from './root';

@NgModule({
  imports: [CommonModule],
  declarations: [
    MessageComponent,
    RootComponent
  ],
})
export class CoreModule {
  static bootstrap: Type<any> = RootComponent;
}
