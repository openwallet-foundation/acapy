import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';

import { Observable } from 'rxjs';

import { environment } from 'src/environments/environment';

@Injectable({
  providedIn: 'root'
})
export class InterceptorService implements HttpInterceptor {
  hostname: string;
  port: number;
  formattedAgentUrl: string;

  constructor() {
    this.hostname = 'localhost';
    this.port = 8031;
    this.formattedAgentUrl = `http://${this.hostname}:${this.port}`;
    console.log('Agent is running on: ' + this.formattedAgentUrl);
  }

  intercept(req: HttpRequest<any>, next: HttpHandler):
    Observable<HttpEvent<any>> {
    req = req.clone({
      url: this.formattedAgentUrl + req.url
    });
    return next.handle(req);
  }
}
