import { toSearchPattern } from "./search-term";

describe("toSearchPattern", () => {
  it.each([
    ["example", "*example*"],
    ["  example.com ", "*example.com*"],
    ["*.example.com", "*.example.com"], // explicit wildcard kept as typed
    ["www.example.co?", "www.example.co?"],
    ["", ""],
    ["   ", ""],
  ])("%j → %j", (term, expected) => {
    expect(toSearchPattern(term)).toBe(expected);
  });
});
