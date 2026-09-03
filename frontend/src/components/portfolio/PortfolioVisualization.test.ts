import { describe, expect, it } from "vitest";
import type { PortfolioValueSnapshotPoint } from "../../models/portfolio";
import {
  buildChronologicalPortfolioPoints,
  buildCompletedHalfHourlyCandles,
  buildCompletedPortfolioCandles,
  mergeLatestSnapshotIntoDailyHistory,
  mergeLatestSnapshotIntoWeeklyHistory,
} from "./PortfolioVisualization";

function point(minute: number, total: number): PortfolioValueSnapshotPoint {
  return {
    ts: `2026-09-02T09:${String(minute).padStart(2, "0")}:00.000Z`,
    holdings_value_try: total - 100_000,
    cash_value_try: 100_000,
    total_value_try: total,
  };
}

function datedPoint(ts: string, total: number): PortfolioValueSnapshotPoint {
  return {
    ts,
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

describe("buildCompletedPortfolioCandles", () => {
  it.each(["1H", "1A"] as const)("%s icin snapshot'lardan gunluk OHLC uretir", (range) => {
    const candles = buildCompletedPortfolioCandles(
      [
        datedPoint("2026-09-01T06:00:00Z", 3_280_000),
        datedPoint("2026-09-01T09:00:00Z", 3_290_000),
        datedPoint("2026-09-01T12:00:00Z", 3_275_000),
        datedPoint("2026-09-01T18:00:00Z", 3_285_000),
      ],
      range,
      new Date("2026-09-02T03:00:00Z").getTime(),
    );

    expect(candles).toEqual([{
      ts: "2026-09-01T00:00:00+03:00",
      open: 3_280_000,
      high: 3_290_000,
      low: 3_275_000,
      close: 3_285_000,
      range: [3_275_000, 3_290_000],
    }]);
  });

  it("1Y icin gunluk toplamları haftalik OHLC'de birlestirir", () => {
    const candles = buildCompletedPortfolioCandles(
      [
        datedPoint("2026-08-24T18:00:00Z", 3_200_000),
        datedPoint("2026-08-26T18:00:00Z", 3_240_000),
        datedPoint("2026-08-27T18:00:00Z", 3_180_000),
        datedPoint("2026-08-28T18:00:00Z", 3_230_000),
      ],
      "1Y",
      new Date("2026-09-02T03:00:00Z").getTime(),
    );

    expect(candles).toEqual([{
      ts: "2026-08-24T00:00:00+03:00",
      open: 3_200_000,
      high: 3_240_000,
      low: 3_180_000,
      close: 3_230_000,
      range: [3_180_000, 3_240_000],
    }]);
  });

  it("tamamlanmamis gunu muma donusturmez", () => {
    const candles = buildCompletedPortfolioCandles(
      [datedPoint("2026-09-02T09:00:00Z", 3_280_000)],
      "1H",
      new Date("2026-09-02T12:00:00Z").getTime(),
    );

    expect(candles).toEqual([]);
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

describe("mergeLatestSnapshotIntoDailyHistory", () => {
  it("gecmis gunleri koruyup bugunun noktasini son snapshot ile degistirir", () => {
    const history = [
      datedPoint("2026-09-01T00:00:00+03:00", 3_200_000),
      datedPoint("2026-09-02T00:00:00+03:00", 3_250_000),
      datedPoint("2026-09-03T00:00:00+03:00", 3_300_000),
    ];
    const latest = datedPoint("2026-09-03T14:15:00+03:00", 3_303_969);

    const merged = mergeLatestSnapshotIntoDailyHistory(history, latest);

    expect(merged).toEqual([history[0], history[1], latest]);
  });
});

describe("mergeLatestSnapshotIntoWeeklyHistory", () => {
  it("gecmis haftalari koruyup mevcut haftayi son snapshot ile degistirir", () => {
    const history = [
      datedPoint("2026-08-28T00:00:00+03:00", 3_200_000),
      datedPoint("2026-08-31T00:00:00+03:00", 3_250_000),
      datedPoint("2026-09-02T00:00:00+03:00", 3_300_000),
    ];
    const latest = datedPoint("2026-09-03T14:15:00+03:00", 3_303_969);

    const merged = mergeLatestSnapshotIntoWeeklyHistory(history, latest);

    expect(merged).toEqual([history[0], latest]);
  });
});
