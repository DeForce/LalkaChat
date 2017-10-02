import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs/BehaviorSubject';
import { Http, Response } from '@angular/http';
import { Observable } from 'rxjs/Observable';
import 'rxjs/add/operator/toPromise'
import 'rxjs/add/observable/dom/webSocket';
import 'rxjs/add/operator/filter';

import { Message, MessageType, RxWebsocketSubject } from '../models';
import { WEBSOCKET_URL, WEBCHAT_URL } from '../constants';

@Injectable()
export class MessageService {
  messages$: BehaviorSubject<Message[]>;

  constructor(private http: Http) {
    this.messages$ = new BehaviorSubject([]);
    const socket$ = new RxWebsocketSubject(WEBSOCKET_URL);

    socket$
      .filter((message: Message) => message.type === 'message')
      .subscribe((message: Message) => this.newMessage(message));

    socket$
      .filter((message: Message) => message.type === 'command')
      .subscribe((message: Message) => this.process(message));
  }

  deleteMessage(message: Message) {
    const messages = this.messages$.getValue()
      .filter(m => m.id !== message.id);
    this.messages$.next(messages);

    this.http.delete(WEBCHAT_URL + message.id).toPromise();
  }

  cleanUp(timer: number) {
    const now = new Date().getTime() / 1000;
    const messages = this.messages$
      .getValue()
      .filter(message => Math.abs(now - message.unixtime) < timer);

    this.messages$.next(messages);
  }

  protected newMessage(message: Message) {
    const messages = [
      ...this.messages$.getValue(),
      message
    ];

    this.messages$.next(messages);
  }

  protected removeByIds(ids: Array<string>) {
    const messages = this.messages$
      .getValue()
      .filter(message => ids.indexOf(message.id) < 0);

    this.messages$.next(messages);
  }

  protected removeByUsernames(usernames: Array<string>) {
    const names = usernames.map(value => value.toLowerCase());
    const messages = this.messages$
      .getValue()
      .filter(message => names.indexOf(message.user.toLowerCase()) < 0);

    this.messages$.next(messages);
  }

  protected replaceByIds(message: Message) {
    const messages = this.messages$.getValue().map(
      (m: Message) => {
        const index = (<any>message).ids.indexOf(message.id);

        if (index >= 0) {
          m.text = message.text;
          m.emotes = [];
          (<any>m).bttv_emotes = {};
        }

        return m;
      }
    );

    this.messages$.next(messages);
  }

  protected replaceByUsernames(message: Message) {
    const names = (<any>message.user).map(value => value.toLowerCase());

    const messages = this.messages$.getValue().map(
      (m: Message) => {
        const user = message.user.toLowerCase();
        const index = names.indexOf(user);

        if (index >= 0) {
          m.text = message.text;
          m.emotes = [];
          (<any>m).bttv_emotes = {};
        }

        return m;
      }
    );

    this.messages$.next(messages);
  }

  protected process(message: Message) {
    switch (message.command) {
      case 'reload': {
        window.location.reload();
        break;
      }

      case 'remove_by_user': {
        this.removeByUsernames((<any>message).user);
        break;
      }

      case 'remove_by_id': {
        this.removeByIds((<any>message).ids)
        break;
      }

      case 'replace_by_id': {
        this.replaceByIds(message);
        break;
      }

      case 'replace_by_user': {
        this.replaceByUsernames(message);
        break;
      }

      default: {
        console.log('Got unknown command ', message.command);
      }
    }
  }
}
