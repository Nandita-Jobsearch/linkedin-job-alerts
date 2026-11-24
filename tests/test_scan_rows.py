import math

import pandas as pd

import scan


def test_empty_float_columns_become_none(monkeypatch):
    """JobSpy hands back all-NaN float columns; rows must carry None, not NaN."""
    df = pd.DataFrame([{"site": "linkedin", "id": "1", "title": "SDR",
                        "job_url": "https://j/1", "company_url_direct": float("nan"),
                        "min_amount": float("nan")}])
    monkeypatch.setattr(scan, "scrape_jobs", lambda **kw: df)
    (row,) = scan._one("linkedin", "sdr", "Ireland")
    for key in ("company_url_direct", "min_amount", "company_rating"):
        assert row[key] is None, key
    assert not any(isinstance(v, float) and math.isnan(v) for v in row.values())
