import { Component, computed, DestroyRef, inject, OnInit, signal } from "@angular/core";
import { takeUntilDestroyed, toObservable } from "@angular/core/rxjs-interop";
import { form, FormField } from "@angular/forms/signals";
import { ActivatedRoute, Router, RouterLink } from "@angular/router";
import { debounceTime, distinctUntilChanged, filter, map, skip } from "rxjs";
import { PdnsService } from "../../core/services/pdns.service";
import { SearchResult } from "../../shared/models/pdns.model";
import { TranslatePipe } from "@ngx-translate/core";

@Component({
  selector: "app-search",
  imports: [RouterLink, FormField, TranslatePipe],
  templateUrl: "./search.component.html",
  styleUrl: "./search.component.css",
})
export class SearchComponent implements OnInit {
  private readonly pdns = inject(PdnsService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly searchModel = signal({
    search: "",
    objectType: "all" as "all" | "zone" | "record" | "comment",
    max: 100,
  });
  readonly searchForm = form(this.searchModel);

  readonly results = signal<SearchResult[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly hasSearched = signal(false);

  readonly zones = computed(() => this.results().filter((r) => r.object_type === "zone"));
  readonly records = computed(() => this.results().filter((r) => r.object_type === "record"));
  readonly comments = computed(() => this.results().filter((r) => r.object_type === "comment"));

  // skip(1) évite une double recherche lors du chargement initial avec param URL
  private readonly searchChanges$ = toObservable(this.searchModel).pipe(
    map((m) => m.search),
    skip(1),
    debounceTime(400),
    distinctUntilChanged(),
  );

  async ngOnInit(): Promise<void> {
    const q = this.route.snapshot.queryParamMap.get("q") ?? "";
    if (q) {
      this.searchModel.update((m) => ({ ...m, search: q }));
      await this.doSearch(q);
    }

    this.searchChanges$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((val) => {
      void this.router.navigate([], {
        queryParams: { q: val || null },
        queryParamsHandling: "merge",
      });
      if (val && val.length >= 2) void this.doSearch(val);
      else if (!val) this.results.set([]);
    });

    // When the navbar triggers a new search (component reused, ngOnInit not re-called)
    this.route.queryParamMap
      .pipe(
        skip(1),
        map((p) => p.get("q") ?? ""),
        filter((q) => q !== this.searchModel().search),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((newQ) => {
        this.searchModel.update((m) => ({ ...m, search: newQ }));
        if (newQ) void this.doSearch(newQ);
        else this.results.set([]);
      });
  }

  onSubmit(): void {
    const q = this.searchModel().search.trim();
    if (q) void this.doSearch(q);
  }

  async doSearch(q: string): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    this.hasSearched.set(true);
    try {
      const { objectType, max } = this.searchModel();
      const data = await this.pdns.search(q, max, objectType);
      this.results.set(data);
    } catch {
      this.error.set("Error occurred while searching. Please check that the PDNS backend is accessible.");
    } finally {
      this.isLoading.set(false);
    }
  }

  zoneLink(result: SearchResult): string[] {
    return ["/zones", result.zone_id ?? result.name];
  }

  trackByResult(_: number, r: SearchResult): string {
    return `${r.object_type}-${r.name}-${r.type ?? ""}`;
  }
}
