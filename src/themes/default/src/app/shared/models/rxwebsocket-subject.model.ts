import { Subject } from 'rxjs/Subject';
import { Observable } from 'rxjs/Observable';
import { Observer } from 'rxjs/Observer';
import { WebSocketSubject, WebSocketSubjectConfig } from 'rxjs/observable/dom/WebSocketSubject';

export class RxWebsocketSubject<T> extends Subject<T> {
  private socket: WebSocketSubject<any>;

  constructor(
    private url: string,
    private reconnectInterval: number = 1000
  ) {
    super();

    this.connect();
  }

  connect() {
    this.socket = new WebSocketSubject(this.url);

    this.socket.subscribe(
      (message) => this.next(message),
      (error: Event) => this.connect()
    );
  }
}
