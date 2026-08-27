"""Yahoo'dan bir aylik 5dk ve bir yillik gunluk OHLCV gecmisini doldurur."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.market import yahoo
from app.repositories.deps import get_market_repository


async def main(selected_interval: str = "all") -> None:
    repository = get_market_repository()
    assets = await repository.get_assets_for_price_update()
    symbols = [asset["symbol"] for asset in assets if asset["symbol"] in yahoo.YAHOO_TICKERS]
    ticker_count = len(yahoo.gerekli_tickerlar(symbols))
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    one_minute_jobs = []
    oldest = now - timedelta(days=29)
    cursor = oldest
    while cursor < now:
        chunk_end = min(cursor + timedelta(days=6), now)
        one_minute_jobs.append(
            {
                "label": f"{cursor:%Y-%m-%d}/{chunk_end:%Y-%m-%d}",
                "interval": "1m",
                "start": cursor,
                "end": chunk_end,
            }
        )
        cursor = chunk_end

    job_sets = {
        "1m": one_minute_jobs,
        "5m": [{"label": "60d", "period": "60d", "interval": "5m"}],
        "1d": [{"label": "2y", "period": "2y", "interval": "1d"}],
    }
    jobs = (
        job_sets["1m"] + job_sets["5m"] + job_sets["1d"]
        if selected_interval == "all"
        else job_sets[selected_interval]
    )
    planned_calls = ticker_count * len(jobs)
    used = await repository.get_api_usage_today()
    quota = settings.market_api_daily_quota
    if quota > 0 and used + planned_calls > quota:
        raise RuntimeError(
            f"gecmis doldurma kotayi asar: kullanilan={used}, "
            f"planlanan={planned_calls}, tavan={quota}"
        )

    total_downloaded = 0
    total_written = 0
    for job in jobs:
        try:
            candles = await yahoo.gecmis_mumlari_indir(
                symbols,
                period=job.get("period"),
                interval=job["interval"],
                start=job.get("start"),
                end=job.get("end"),
            )
        finally:
            # Yahoo denemeyi aldiysa hata durumunda da gercek ticker sayisi sayilir.
            await repository.record_api_usage(ticker_count)
        written = await repository.upsert_candles(candles, source="yahoo")
        total_downloaded += len(candles)
        total_written += written
        print(
            f"period={job['label']} interval={job['interval']} "
            f"indirilen={len(candles)} yazilan={written}"
        )

    print(
        f"toplam_indirilen={total_downloaded} toplam_yazilan={total_written} "
        f"yahoo_istek={planned_calls}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", choices=("1m", "5m", "1d", "all"), default="all")
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(args.interval))
