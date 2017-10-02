import { Component, OnInit, ChangeDetectionStrategy, Input, HostListener } from '@angular/core';
import * as twemoji from 'twemoji';

import { Message, Emote, MessageService } from 'app/shared';

@Component({
  selector: 'lc-message',
  templateUrl: './message.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MessageComponent {
  @Input()
  message: Message;

  showRemoveButton: boolean;

  @HostListener('mouseenter')
  onEnter() {
    this.showRemoveButton = true;
  }

  @HostListener('mouseleave')
  onLeave() {
    this.showRemoveButton = false;
  }

  get platformUrl(): string {
    return this.message.platform.icon || `./img/sources/${this.message.platform.id}.png`;
  }

  get deleteUrl(): string {
    return `/img/gui/delete.png`;
  }

  get messageText(): string {
    const message = twemoji.parse(this.message.text);

    return this.message.emotes.reduce(
      (m: string, emote: Emote) => this.replaceEmotes(m, emote),
      message
    );
  }

  protected remove() {
    this.messageService.deleteMessage(this.message);
  }

  protected replaceEmotes(message: string, emote: Emote): string {
    const regex = new RegExp(emote.id, 'g');

    return message.replace(regex, `<img class="smile" draggable="false" src="${emote.url}" />`);
  }

  constructor(protected messageService: MessageService) {}
}
