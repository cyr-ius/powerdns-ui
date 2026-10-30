import { NgTemplateOutlet } from "@angular/common";
import { Component, inject } from "@angular/core";
import { TranslatePipe } from "@ngx-translate/core";
import { ZoneDetailStore } from "../zone-detail.store";

/** Result panels of the SOA sync and e-mail security (SPF / DMARC / DKIM) checks. */
@Component({
  selector: "app-zone-checks",
  imports: [TranslatePipe, NgTemplateOutlet],
  templateUrl: "./zone-checks.component.html",
  host: { class: "d-block" },
})
export class ZoneChecksComponent {
  private readonly store = inject(ZoneDetailStore);

  readonly soaCheck = this.store.soaCheck;
  readonly isCheckingSoa = this.store.isCheckingSoa;
  readonly soaCheckError = this.store.soaCheckError;
  readonly showSoaPanel = this.store.showSoaPanel;

  readonly emailCheck = this.store.emailCheck;
  readonly isCheckingEmail = this.store.isCheckingEmail;
  readonly emailCheckError = this.store.emailCheckError;
  readonly showEmailPanel = this.store.showEmailPanel;
}
