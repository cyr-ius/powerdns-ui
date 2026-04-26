import { Component, OnInit, inject } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { AuthService } from './core/services/auth.service';
import { ThemeService } from './core/services/theme.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  template: '<router-outlet />',
})
export class App implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  constructor() {
    inject(ThemeService);
    const translate = inject(TranslateService);
    const lang = localStorage.getItem('lang') ?? navigator.language.split('-')[0];
    const supported = ['en', 'fr', 'es'];
    translate.use(supported.includes(lang) ? lang : 'en');
  }

  async ngOnInit(): Promise<void> {
    const params = new URLSearchParams(window.location.hash.substring(1));
    const token = params.get('token');
    if (token) {
      await this.auth.loginWithToken(token);
      window.history.replaceState({}, '', window.location.pathname);
      await this.router.navigate(['/zones']);
    } else if (this.auth.isAuthenticated()) {
      await this.auth.fetchCurrentUser();
    }
  }
}
