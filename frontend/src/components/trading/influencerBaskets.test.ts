import { describe, expect, it } from "vitest";
import type { PercentageBasketPreview } from "../../models/trading";
import { buildInfluencerBasketPlan, INFLUENCER_BASKETS } from "./influencerBaskets";

describe("influencer basket definitions", () => {
  it("keeps every fictional demo basket at 100 percent", () => {
    for (const basket of INFLUENCER_BASKETS) {
      expect(basket.allocations.reduce((total, item) => total + item.weightPct, 0)).toBe(100);
    }
  });

  it("contains domestic, foreign, crypto, commodity and FX symbols", () => {
    const symbols = new Set(
      INFLUENCER_BASKETS.flatMap((basket) => basket.allocations.map((item) => item.symbol)),
    );
    expect([...symbols]).toEqual(
      expect.arrayContaining(["THYAO", "AAPL", "BTC", "GUMUS", "USD/TRY"]),
    );
  });
});

describe("buildInfluencerBasketPlan", () => {
  it("maps the backend TRY-priced preview into the UI plan", () => {
    const preview: PercentageBasketPreview = {
      available_balance: 10_215,
      investable_gross: 10_000,
      estimated_gross: 9_500,
      estimated_reserve: 9_704.25,
      remaining_balance: 510.75,
      unavailable_symbols: [],
      unaffordable_symbols: ["AAPL"],
      items: [{
        symbol: "BTC",
        asset_name: "Bitcoin",
        asset_class: "CRYPTO",
        currency: "USD",
        weight_pct: 10,
        quoted_price_try: 4_000_000,
        quantity: 0.00025,
        estimated_gross: 1_000,
        estimated_reserve: 1_021.5,
      }],
    };

    const plan = buildInfluencerBasketPlan(INFLUENCER_BASKETS[0], preview);

    expect(plan.items[0]).toMatchObject({
      symbol: "BTC",
      weightPct: 10,
      quotedPriceTry: 4_000_000,
    });
    expect(plan.skippedSymbols).toEqual(["AAPL"]);
    expect(plan.estimatedReserve).toBe(9_704.25);
  });
});
