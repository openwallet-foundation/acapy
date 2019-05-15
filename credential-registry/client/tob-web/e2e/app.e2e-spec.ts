import { BaseApp2Page } from './app.po';

describe('base-app2 App', () => {
  let page: BaseApp2Page;

  beforeEach(() => {
    page = new BaseApp2Page();
  });

  it('should display message saying app works', () => {
    page.navigateTo();
    expect(page.getParagraphText()).toEqual('Theming your app');
  });
});
