import { Component, computed, input } from "@angular/core";
import { TranslatePipe } from "@ngx-translate/core";
import { PASSWORD_MIN_LENGTH, passwordCriteria } from "../../utils/password-policy";

/** Live checklist of the password policy, and of the confirmation when given. */
@Component({
  selector: "app-password-policy",
  imports: [TranslatePipe],
  templateUrl: "./password-policy.component.html",
  host: { class: "d-block" },
})
export class PasswordPolicyComponent {
  readonly password = input.required<string>();
  /** Confirmation field value; leave unset when the form has none. */
  readonly confirm = input<string>();

  protected readonly minLength = PASSWORD_MIN_LENGTH;
  protected readonly criteria = computed(() => passwordCriteria(this.password()));
  protected readonly confirmState = computed(() => {
    const confirm = this.confirm();
    if (confirm === undefined || confirm === "") return null;
    return confirm === this.password() ? "match" : "mismatch";
  });
}
