/** Password policy, checked again by the backend (app/dependencies.py). */
export const PASSWORD_MIN_LENGTH = 12;

export interface PasswordCriterion {
  /** Translation key of the criterion, under PASSWORD_POLICY. */
  readonly key: string;
  readonly met: boolean;
}

export function passwordCriteria(password: string): PasswordCriterion[] {
  return [
    { key: "MIN_LENGTH", met: password.length >= PASSWORD_MIN_LENGTH },
    { key: "LOWERCASE", met: /\p{Ll}/u.test(password) },
    { key: "UPPERCASE", met: /\p{Lu}/u.test(password) },
    { key: "DIGIT", met: /\p{Decimal_Number}/u.test(password) },
    { key: "SYMBOL", met: /[^\p{L}\p{N}]/u.test(password) },
  ];
}

export function passwordMeetsPolicy(password: string): boolean {
  return passwordCriteria(password).every((c) => c.met);
}
