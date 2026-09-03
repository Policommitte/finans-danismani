import { describe, expect, it } from "vitest";
import { parseBudgetInput } from "./budgetInput";

describe("parseBudgetInput", () => {
  it.each([
    ["10000", 10_000],
    ["10.000 TL", 10_000],
    ["10,000", 10_000],
    ["₺75000", 75_000],
    ["25 bin", 25_000],
    ["50k", 50_000],
    ["1,5 milyon", 1_500_000],
    ["2 milyon lira", 2_000_000],
    ["1.250,50", 1_250.5],
    ["yaklaşık 40 bin tl yatırmak istiyorum", 40_000],
  ])("parses %s", (input, expected) => {
    expect(parseBudgetInput(input)).toBe(expected);
  });

  it.each(["", "bilmiyorum", "sıfır", "0", "-500"])("rejects %s", (input) => {
    expect(parseBudgetInput(input)).toBeNull();
  });
});
