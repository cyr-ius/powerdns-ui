import { Injectable, effect, signal } from "@angular/core";

export type Theme = "light" | "dark" | "auto";

@Injectable({ providedIn: "root" })
export class ThemeService {
  private readonly STORAGE_KEY = "pdns_theme";
  private readonly _theme = signal<Theme>(this._loadTheme());

  readonly theme = this._theme.asReadonly();

  constructor() {
    this._applyTheme(this._theme());

    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (this._theme() === "auto") {
        this._applyTheme("auto");
      }
    });

    effect(() => {
      this._applyTheme(this._theme());
    });
  }

  setTheme(theme: Theme): void {
    localStorage.setItem(this.STORAGE_KEY, theme);
    this._theme.set(theme);
  }

  cycleTheme(): void {
    const order: Theme[] = ["auto", "light", "dark"];
    const current = this._theme();
    const next = order[(order.indexOf(current) + 1) % order.length];
    this.setTheme(next);
  }

  themeIcon(): string {
    switch (this._theme()) {
      case "light":
        return "bi-sun";
      case "dark":
        return "bi-moon";
      default:
        return "bi-circle-half";
    }
  }

  themeLabel(): string {
    switch (this._theme()) {
      case "light":
        return "Light";
      case "dark":
        return "Dark";
      default:
        return "Auto";
    }
  }

  private _loadTheme(): Theme {
    const stored = localStorage.getItem(this.STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "auto") {
      return stored;
    }
    return "auto";
  }

  private _applyTheme(theme: Theme): void {
    const html = document.documentElement;
    if (theme === "auto") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      html.setAttribute("data-bs-theme", prefersDark ? "dark" : "light");
    } else {
      html.setAttribute("data-bs-theme", theme);
    }
  }
}
