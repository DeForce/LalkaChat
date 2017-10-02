import { Injectable } from '@angular/core';
import { Http, Response } from '@angular/http';
import { Observable } from 'rxjs/Observable';
import 'rxjs/add/operator/map';
import 'rxjs/add/operator/catch';

@Injectable()
export class SettingsService {
  constructor(private http: Http) { }

  getSettings() {
    const name: string = window.location.pathname.indexOf('gui') !== -1
      ? 'gui'
      : 'chat';

    const url = `http://${window.location.host}/rest/webchat/style/${name}`;

    return this.http.get(url)
      .map(value => this.map(value));
  }

  private map(value: Response): any {
    return value.json();
  }
}
