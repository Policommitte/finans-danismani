import { describe, expect, it } from "vitest";
import type { PortfolioValueSnapshotPoint } from "../../models/portfolio";
import {
  buildChronologicalPortfolioPoints,
  buildCompletedHalfHourlyCandles,
} from "./PortfolioVisualization";

function point(minute: number, total: number): PortfolioValueSnapshotPoint {
  return {
    ts: `2026-09-02T09:${String(minute).padStart(2, "0")}:00.000Z`,
    holdings_value_try: total - 100_000,
    cash_value_try: 100_000,
    total_value_try: total,
  };
}

describe("buildCompletedHalfHourlyCandles", () => {
  it("başarılı fiyat turlarından doğru OHLC üretir", () => {
    const candles = buildCompletedHalfHourlyCandles([
      point(0, 3_280_000),
      point(5, 3_282_000),
      point(10, 3_279_000),
      point(15, 3_285_000),
      point(20, 3_281_000),
      point(25, 3_283_000),
    ]);

    expect(candles).toEqual([
      {
        ts: "2026-09-02T09:00:00.000Z",
        open: 3_280_000,
        high: 3_285_000,
        low: 3_279_000,
        close: 3_283_000,
        range: [3_279_000, 3_285_000],
      },
    ]);
  });

  it("başarılı turlar eşit aralıklı olmasa da tamamlanmış mumu üretir", () => {
    const candles = buildCompletedHalfHourlyCandles([
      point(0, 3_280_000),
      point(5, 3_282_000),
      point(15, 3_285_000),
      point(20, 3_281_000),
      point(25, 3_283_000),
    ]);

    expect(candles).toEqual([
      {
        ts: "2026-09-02T09:00:00.000Z",
        open: 3_280_000,
        high: 3_285_000,
        low: 3_280_000,
        close: 3_283_000,
        range: [3_280_000, 3_285_000],
      },
    ]);
  });
});

describe("buildChronologicalPortfolioPoints", () => {
  it("en yeni baÅŸarÄ±lÄ± snapshot'i Ã§izginin en saÄŸÄ±na yerleÅŸtirir", () => {
    const latest = point(15, 3_285_000);
    const oldest = point(5, 3_280_000);
    const middle = point(10, 3_282_000);

    const points = buildChronologicalPortfolioPoints([latest, oldest, middle], 1);

    expect(points.map((item) => item.ts)).toEqual([oldest.ts, middle.ts, latest.ts]);
    expect(points.at(-1)?.total_value_try).toBe(3_285_000);
  });
});
