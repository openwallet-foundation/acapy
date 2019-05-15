import { Directive, Input, Renderer, TemplateRef, ViewContainerRef } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

interface LangContext {
  $implicit: string;
  lang: string;
}

@Directive({
    selector: '[withLang]'
})
export class WithLangDirective {
  constructor(
    private _renderer: Renderer,
    private _templateRef: TemplateRef<LangContext>,
    private _translate: TranslateService,
    private _viewRef: ViewContainerRef,
  ) {}

  @Input()
  set withLang(value: string) {
    this._viewRef.clear();

    if(! value || value === this._translate.currentLang) {
      this._viewRef.createEmbeddedView(this._templateRef, {
        $implicit: this._translate.currentLang,
        lang: this._translate.currentLang,
      });
    }
  }
}
