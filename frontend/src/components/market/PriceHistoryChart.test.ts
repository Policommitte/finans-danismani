import { describe, expect, it } from "vitest";

import type { Candle } from "../../models/market";
import { visibleRangeStart } from "./PriceHistoryChart";

function candle(day: string, hour = "07:00:00"): Candle {
  return {
    time: Math.floor(new Date(`${day}T${hour}Z`).getTime() / 1000),
    open: 100,
    high: 101,
    low: 99,
    close: 100,
    volume: 1,
  };
}

describe("visibleRangeStart", () => {
  const tradingDays = ["2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-24", "2026-08-25"];
  const candles = tradingDays.flatMap((day) => [candle(day), candle(day, "08:00:00")]);

  it("1G icin son islem gununun ilk mumundan baslar", () => {
    expect(visibleRangeStart(candles, "1d")).toBe(candle("2026-08-25").time);
  });

  it("5G icin hafta sonunu saymadan besinci islem gununden baslar", () => {
    expect(visibleRangeStart(candles, "5d")).toBe(candle("2026-08-19").time);
  });

  it("1A icin bir ay onceki tarihten sonraki ilk mumu kullanir", () => {
    const monthlyCandles = [candle("2026-07-24"), candle("2026-07-25"), candle("2026-08-25")];

    expect(visibleRangeStart(monthlyCandles, "1m")).toBe(candle("2026-07-25").time);
  });
});

describe("colorForecastByDirection", () => {
  it("paints rising segments green and falling segments red", async () => {
    const { colorForecastByDirection } = await import("./PriceHistoryChart");
    const colored = colorForecastByDirection([
      { time: 1, value: 100 },
      { time: 2, value: 105 },
      { time: 3, value: 102 },
      { time: 4, value: 102 },
    ]);
    expect(colored.map((p) => p.color)).toEqual(["#26a69a", "#26a69a", "#ef5350", "#26a69a"]);
  });
});
