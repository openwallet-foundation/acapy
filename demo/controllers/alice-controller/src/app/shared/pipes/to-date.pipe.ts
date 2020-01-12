import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'toDate'
})
export class ToDatePipe implements PipeTransform {

  transform(value: any, ...args: any[]): any {
    return new Date(value ? value.toString().replace(' ', 'T') : null);
  }

}
