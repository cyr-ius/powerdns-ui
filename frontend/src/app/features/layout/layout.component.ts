import { Component, OnDestroy, OnInit, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from "@angular/router";
import { TranslatePipe } from "@ngx-translate/core";
import { AppInfoService } from "../../core/services/app-info.service";
import { AuthService } from "../../core/services/auth.service";
import { ServerService } from "../../core/services/server.service";
import { ThemeService } from "../../core/services/theme.service";

const COLLAPSE_STORAGE_KEY = "pdns_sidebar_collapsed";
// Below this width the sidebar falls back to its icon rail on its own; above it
// the user's own choice wins.
const AUTO_COLLAPSE_WIDTH = 1200;

@Component({
  selector: "app-layout",
  imports: [RouterOutlet, RouterLink, RouterLinkActive, FormsModule, TranslatePipe],
  templateUrl: "./layout.component.html",
  styleUrl: "./layout.component.css",
})
export class LayoutComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  readonly themeService = inject(ThemeService);
  readonly server = inject(ServerService);
  readonly appInfo = inject(AppInfoService);
  private readonly router = inject(Router);

  searchQuery = "";

  /** Off-canvas drawer, mobile only. */
  readonly sidebarOpen = signal(false);
  /** Icon-only rail, desktop only. */
  readonly sidebarCollapsed = signal(this.loadCollapsed());

  private readonly narrowScreen = window.matchMedia(`(max-width: ${AUTO_COLLAPSE_WIDTH}px)`);
  private readonly onNarrowChange = (e: MediaQueryListEvent): void => {
    this.sidebarCollapsed.set(e.matches || this.loadCollapsed());
  };

  ngOnInit(): void {
    if (this.auth.isAdmin()) {
      void this.server.init();
    }
    void this.appInfo.load();

    if (this.narrowScreen.matches) {
      this.sidebarCollapsed.set(true);
    }
    this.narrowScreen.addEventListener("change", this.onNarrowChange);
  }

  ngOnDestroy(): void {
    this.narrowScreen.removeEventListener("change", this.onNarrowChange);
  }

  toggleSidebar(): void {
    this.sidebarOpen.update((v) => !v);
  }

  closeSidebar(): void {
    this.sidebarOpen.set(false);
  }

  toggleCollapsed(): void {
    const collapsed = !this.sidebarCollapsed();
    this.sidebarCollapsed.set(collapsed);
    localStorage.setItem(COLLAPSE_STORAGE_KEY, String(collapsed));
  }

  logout(): void {
    this.auth.logout();
  }

  onSearch(): void {
    const q = this.searchQuery.trim();
    if (q) {
      void this.router.navigate(["/search"], { queryParams: { q } });
      this.searchQuery = "";
      this.closeSidebar();
    }
  }

  private loadCollapsed(): boolean {
    return localStorage.getItem(COLLAPSE_STORAGE_KEY) === "true";
  }
}
