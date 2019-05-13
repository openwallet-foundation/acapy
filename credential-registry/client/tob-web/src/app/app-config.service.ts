import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable()
export class AppConfigService {
  private _config = {};

  constructor(private _http: HttpClient) { }

  getConfig(): any {
    return this._config;
  }

  loadConfig(data) {
    this._config = data;
    console.log(data);
  }

  loadFromPromise(input: Promise<any>): Promise<any> {
    return input.then(data => this.loadConfig(data));
  }

  loadFromUrl(url: string) {
    return this.loadFromPromise(this._http.get(url).toPromise());
  }
}
