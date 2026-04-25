import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';
import { lmdbGuard } from './core/guards/lmdb.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: '',
    loadComponent: () =>
      import('./features/layout/layout.component').then((m) => m.LayoutComponent),
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'zones', pathMatch: 'full' },
      {
        path: 'zones',
        loadComponent: () =>
          import('./features/zones/zone-list/zone-list.component').then(
            (m) => m.ZoneListComponent,
          ),
      },
      {
        path: 'zones/:id',
        loadComponent: () =>
          import('./features/zones/zone-detail/zone-detail.component').then(
            (m) => m.ZoneDetailComponent,
          ),
      },
      {
        path: 'catalogues',
        loadComponent: () =>
          import('./features/catalogues/catalogues.component').then((m) => m.CataloguesComponent),
      },
      {
        path: 'tsigkeys',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/tsigkeys/tsigkeys.component').then((m) => m.TsigKeysComponent),
      },
      {
        path: 'search',
        loadComponent: () =>
          import('./features/search/search.component').then((m) => m.SearchComponent),
      },
      {
        path: 'statistics',
        loadComponent: () =>
          import('./features/statistics/statistics.component').then(
            (m) => m.StatisticsComponent,
          ),
      },
      {
        path: 'profile',
        loadComponent: () =>
          import('./features/profile/profile.component').then((m) => m.ProfileComponent),
      },
      {
        path: 'acme-keys',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/acme-keys/acme-keys.component').then((m) => m.AcmeKeysComponent),
      },
      {
        path: 'server-config',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/server-config/server-config.component').then(
            (m) => m.ServerConfigComponent,
          ),
      },
      {
        path: 'autoprimaries',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/autoprimaries/autoprimaries.component').then(
            (m) => m.AutoprimariesComponent,
          ),
      },
      {
        path: 'networks',
        canActivate: [adminGuard, lmdbGuard],
        loadComponent: () =>
          import('./features/networks/networks.component').then((m) => m.NetworksComponent),
      },
      {
        path: 'views',
        canActivate: [adminGuard, lmdbGuard],
        loadComponent: () =>
          import('./features/views/views.component').then((m) => m.ViewsComponent),
      },
      {
        path: 'admin/users',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/admin/users/users.component').then((m) => m.AdminUsersComponent),
      },
      {
        path: 'admin/accounts',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/admin/accounts/accounts.component').then(
            (m) => m.AdminAccountsComponent,
          ),
      },
      {
        path: 'admin/oidc',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/admin/oidc/oidc.component').then((m) => m.AdminOidcComponent),
      },
      {
        path: 'admin/record-types',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/admin/record-types/record-types.component').then(
            (m) => m.AdminRecordTypesComponent,
          ),
      },
      {
        path: 'admin/audit',
        canActivate: [adminGuard],
        loadComponent: () =>
          import('./features/admin/audit/audit.component').then(
            (m) => m.AdminAuditComponent,
          ),
      },
    ],
  },
  { path: '**', redirectTo: 'zones' },
];
