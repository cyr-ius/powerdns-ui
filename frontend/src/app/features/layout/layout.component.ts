import { Component, OnInit, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from "@angular/router";
import { TranslateModule } from "@ngx-translate/core";
import { AuthService } from "../../core/services/auth.service";
import { ServerService } from "../../core/services/server.service";
import { ThemeService } from "../../core/services/theme.service";

@Component({
  selector: "app-layout",
  imports: [RouterOutlet, RouterLink, RouterLinkActive, FormsModule, TranslateModule],
  templateUrl: "./layout.component.html",
  styleUrl: "./layout.component.css",
})
export class LayoutComponent implements OnInit {
  readonly auth = inject(AuthService);
  readonly themeService = inject(ThemeService);
  readonly server = inject(ServerService);
  private readonly router = inject(Router);

  searchQuery = "";
  readonly sidebarOpen = signal(false);

  ngOnInit(): void {
    if (this.auth.isAdmin()) {
      void this.server.init();
    }
  }

  toggleSidebar(): void {
    this.sidebarOpen.update((v) => !v);
  }

  closeSidebar(): void {
    this.sidebarOpen.set(false);
  }

  logout(): void {
    this.auth.logout();
  }

  onSearch(): void {
    const q = this.searchQuery.trim();
    if (q) {
      void this.router.navigate(["/search"], { queryParams: { q } });
      this.closeSidebar();
    }
  }
}
