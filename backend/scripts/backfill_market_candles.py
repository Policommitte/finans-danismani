"""Yahoo'dan gun ici ve gunluk OHLCV gecmisini doldurur."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.market import yahoo
from app.repositories.deps import get_market_repository


async def main(selected_interval: str = "all", selected_symbols: set[str] | None = None) -> None:
    repository = get_market_repository()
    assets = await repository.get_assets_for_price_update()
    supported = yahoo.desteklenen_semboller()
    symbols = [
        asset["symbol"]
        for asset in assets
        if asset["symbol"] in supported
        and (selected_symbols is None or asset["symbol"] in selected_symbols)
    ]
    if not symbols:
        raise RuntimeError("doldurulacak desteklenen varlik bulunamadi")

    # Yuz binlerce mumu tek JSON/transaction icinde yazmak yerine kucuk
    # gruplar halinde indirip kaydederiz. Bir ticker'daki gecikme de tum
    # varlik paketini kilitlemez.
    symbol_batches = [symbols[index : index + 8] for index in range(0, len(symbols), 8)]
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
        "1h": [{"label": "2y", "period": "2y", "interval": "1h"}],
        "1d": [{"label": "2y", "period": "2y", "interval": "1d"}],
    }
    jobs = (
        job_sets["1m"] + job_sets["5m"] + job_sets["1h"] + job_sets["1d"]
        if selected_interval == "all"
        else job_sets[selected_interval]
    )
    calls_per_job = sum(len(yahoo.gerekli_tickerlar(batch)) for batch in symbol_batches)
    planned_calls = calls_per_job * len(jobs)
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
        for batch_index, batch in enumerate(symbol_batches, start=1):
            batch_calls = len(yahoo.gerekli_tickerlar(batch))
            try:
                candles = await yahoo.gecmis_mumlari_indir(
                    batch,
                    period=job.get("period"),
                    interval=job["interval"],
                    start=job.get("start"),
                    end=job.get("end"),
                )
            finally:
                # Yahoo denemeyi aldiysa hata durumunda da gercek ticker sayisi sayilir.
                await repository.record_api_usage(batch_calls)
            written = await repository.upsert_candles(candles, source="yahoo")
            total_downloaded += len(candles)
            total_written += written
            print(
                f"period={job['label']} interval={job['interval']} "
                f"grup={batch_index}/{len(symbol_batches)} "
                f"indirilen={len(candles)} yazilan={written}"
            )

    print(
        f"toplam_indirilen={total_downloaded} toplam_yazilan={total_written} "
        f"yahoo_istek={planned_calls}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", choices=("1m", "5m", "1h", "1d", "all"), default="all")
    parser.add_argument(
        "--symbols",
        help="Virgulle ayrilmis DB sembolleri; verilmezse tum desteklenenler.",
    )
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    selected = (
        {symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()}
        if args.symbols
        else None
    )
    asyncio.run(main(args.interval, selected))
