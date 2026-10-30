import { passwordMeetsPolicy } from "./password-policy";

// Same cases as backend/tests/test_dependencies.py: both sides must agree.
describe("passwordMeetsPolicy", () => {
  it.each([
    ["Correct-Horse9", true],
    ["Short-Pass9", false], // 11 characters
    ["correct-horse9", false], // no uppercase letter
    ["CORRECT-HORSE9", false], // no lowercase letter
    ["Correct-Horse", false], // no digit
    ["CorrectHorse99", false], // no symbol
  ])("%s → %s", (password, expected) => {
    expect(passwordMeetsPolicy(password)).toBe(expected);
  });
});
