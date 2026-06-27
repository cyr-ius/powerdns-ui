import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { ThemeService } from './core/services/theme.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  template: '<router-outlet />',
})
export class App {
  // Session restoration runs in an APP_INITIALIZER (see app.config.ts) so the
  // auth state is known before the router and guards evaluate the first route.
  constructor() {
    inject(ThemeService);
    const translate = inject(TranslateService);
    const lang = localStorage.getItem('lang') ?? navigator.language.split('-')[0];
    const supported = ['en', 'fr', 'es'];
    translate.use(supported.includes(lang) ? lang : 'en');
  }
}
