from app.services.portfolio import _on_bes_dakikalik_dilimlere_indir


def test_performance_rows_are_reduced_to_latest_value_per_15_minute_bucket():
    rows = [
        {"ts": "2026-08-20T10:01:00+03:00", "total_value_try": 100},
        {"ts": "2026-08-20T10:14:59+03:00", "total_value_try": 110},
        {"ts": "2026-08-20T10:15:00+03:00", "total_value_try": 120},
        {"ts": "2026-08-20T10:29:59+03:00", "total_value_try": 130},
    ]

    result = _on_bes_dakikalik_dilimlere_indir(rows)

    assert result == [
        {"ts": "2026-08-20T10:00:00+03:00", "total_value_try": 110},
        {"ts": "2026-08-20T10:15:00+03:00", "total_value_try": 130},
    ]
