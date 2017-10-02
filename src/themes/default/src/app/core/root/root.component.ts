import { Component, ChangeDetectionStrategy, DoCheck, AfterViewChecked, HostBinding, ElementRef } from '@angular/core';
import { Observable } from 'rxjs/Observable';
import 'rxjs/add/observable/fromEvent';
import 'rxjs/add/observable/interval';
import 'rxjs/add/operator/debounceTime';

import { Message, MessageService, SettingsService } from 'app/shared';

@Component({
  selector: 'lc-root',
  templateUrl: './root.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RootComponent implements DoCheck, AfterViewChecked {
  @HostBinding('style.height.px')
  height = window.innerHeight;

  @HostBinding('style.overflow-y')
  scroll = 'scroll';

  messages: Observable<Array<Message>>;

  element: HTMLElement;

  autoscroll: boolean;

  constructor(
    elementRef: ElementRef,
    settingsService: SettingsService,
    private messageService: MessageService
  ) {
    this.messages = messageService.messages$;
    this.element = elementRef.nativeElement;

    settingsService
      .getSettings()
      .subscribe((settings) => this.configure(settings));

    Observable
      .fromEvent(window, 'resize')
      .debounceTime(250)
      .subscribe(() => this.height = window.innerHeight);
  }

  configure(settings) {
    if (settings.timer > 0) {
      Observable
        .interval(500)
        .subscribe(() => this.messageService.cleanUp(settings.timer))
    }
  }

  ngDoCheck() {
    const offset = Math.abs(this.element.scrollTop + this.element.clientHeight - this.element.scrollHeight)
    this.autoscroll = offset <= this.element.scrollHeight * 0.05;
  }

  ngAfterViewChecked() {
    if (this.autoscroll) {
      this.element.scrollTop = this.element.scrollHeight;
    }
  }
}
