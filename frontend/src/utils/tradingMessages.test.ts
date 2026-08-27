import { describe, expect, it } from "vitest";

import { localizeTradingMessage } from "./tradingMessages";

describe("localizeTradingMessage", () => {
  const insufficientShares = "Bekleyen emirler dusuldugunde satilabilir hisse adedi yetersiz.";

  it("restores Turkish characters", () => {
    expect(localizeTradingMessage(insufficientShares, "tr")).toBe(
      "Bekleyen emirler düşüldüğünde satılabilir hisse adedi yetersiz.",
    );
  });

  it("returns the English equivalent", () => {
    expect(localizeTradingMessage(insufficientShares, "en")).toBe(
      "There are not enough shares available to sell after pending orders are deducted.",
    );
  });
});
