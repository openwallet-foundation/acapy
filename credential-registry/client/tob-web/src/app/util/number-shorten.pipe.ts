import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'shortNumber',
  pure: true
})
export class NumberShortenPipe implements PipeTransform {
  constructor() {
  }

  transform(value: any, args?: any): any {
    let ret = '';
    let suffix = '';
    let maxlen = arguments[1] || 4;
    let sfxs = ['K', 'M', 'B', 'T'];
    let intlen = 0;
    if(! value) ret = '0';
    else {
      for(let sfx of sfxs) {
        intlen = ('' + Math.floor(value)).length;
        if(intlen <= maxlen - suffix.length)
          break;
        value /= 1000;
        suffix = sfx;
      }
      let decs = Math.max(0, maxlen - intlen - 1 - suffix.length);
      let rnd = Math.pow(10, decs);
      ret = ('' + (Math.round(value * rnd) / rnd)) + suffix;
    }
    return ret;
  }
}
