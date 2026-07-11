import { Component, OnInit, inject } from "@angular/core";
import { RouterLink } from "@angular/router";
import { TranslatePipe } from "@ngx-translate/core";
import { AppInfoService } from "../../core/services/app-info.service";

@Component({
  selector: "app-about",
  imports: [RouterLink, TranslatePipe],
  templateUrl: "./about.component.html",
})
export class AboutComponent implements OnInit {
  readonly appInfoSvc = inject(AppInfoService);

  async ngOnInit(): Promise<void> {
    await this.appInfoSvc.load();
    await this.appInfoSvc.checkHealth();
  }

  refreshHealth(): void {
    void this.appInfoSvc.checkHealth();
  }
}
