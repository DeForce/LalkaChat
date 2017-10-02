import { NgModule } from '@angular/core';
import { HttpModule } from '@angular/http';

import { MessageService, SettingsService } from './services';

@NgModule({
  imports: [HttpModule],
  providers: [
    MessageService,
    SettingsService
  ]
})
export class SharedModule { }
