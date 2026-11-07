"""Join the unchanged flood table to a documented city-reference ERA5 series.

The reference point is an OSM Nominatim result for Ho Chi Minh City. Its
rainfall must not be described as rainfall measured at an observation site.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
ORIGINAL = HERE / "Flood_event_locations.tab"
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)
REFERENCE_LAT = 10.7737261
REFERENCE_LON = 106.7166008
VALID_CLASSES = {"Low", "Moderate", "Heavy", "Severe"}


def get_daily_rain(start: str, end: str) -> tuple[pd.DataFrame, str, dict]:
    params = {
        "latitude": REFERENCE_LAT,
        "longitude": REFERENCE_LON,
        "start_date": start,
        "end_date": end,
        "daily": "precipitation_sum",
        "models": "era5",
        "timezone": "Asia/Bangkok",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "SC203-flood-data-preparation/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = json.load(response)
    if payload.get("error"):
        raise RuntimeError(payload.get("reason", "Weather API error"))
    daily = payload["daily"]
    rain = pd.DataFrame({
        "date_iso": daily["time"],
        "rain_era5_city_day_mm": daily["precipitation_sum"],
    })
    rain["rain_era5_city_prev3d_mm"] = (
        rain["rain_era5_city_day_mm"].shift(1).rolling(3, min_periods=3).sum()
    )
    return rain, url, {k: payload.get(k) for k in ("latitude", "longitude", "timezone", "utc_offset_seconds", "daily_units")}


def main() -> None:
    raw = pd.read_csv(ORIGINAL, sep="\t", dtype=str, keep_default_na=False)
    dates = pd.to_datetime(raw["Date"], format="%d/%m/%Y", errors="coerce")
    valid_dates = dates.dropna()
    rain, url, response_metadata = get_daily_rain(
        (valid_dates.min() - pd.Timedelta(days=3)).strftime("%Y-%m-%d"),
        valid_dates.max().strftime("%Y-%m-%d"),
    )
    rain.to_csv(OUT / "era5_hcm_reference_daily.csv", index=False)

    prepared = raw.copy()
    prepared["date_iso"] = dates.dt.strftime("%Y-%m-%d").fillna("")
    prepared["water_height_max_m"] = pd.to_numeric(
        raw["Water height max (cm)"], errors="coerce"
    ) / 100
    prepared["depth_class_label"] = raw["Depth class"].where(
        raw["Depth class"].isin(VALID_CLASSES), ""
    )
    prepared = prepared.merge(rain, on="date_iso", how="left", validate="many_to_one")
    prepared["rain_reference"] = "HCMC city reference point; ERA5 0.25 degree grid"
    prepared.loc[prepared["date_iso"].eq(""), "rain_reference"] = ""
    assert len(prepared) == len(raw)
    assert prepared["OBJECTID"].tolist() == raw["OBJECTID"].tolist()

    prepared.to_csv(OUT / "flood_observations_enriched.csv", index=False, encoding="utf-8-sig")
    audit = {
        "original_rows": len(raw),
        "numeric_depth_rows": int(prepared["water_height_max_m"].notna().sum()),
        "known_depth_class_rows": int(prepared["depth_class_label"].ne("").sum()),
        "class_only_extra_rows": int((prepared["water_height_max_m"].isna() & prepared["depth_class_label"].ne("")).sum()),
        "rows_with_parseable_date": int(dates.notna().sum()),
        "rows_with_era5_daily_rain": int(prepared["rain_era5_city_day_mm"].notna().sum()),
        "rows_with_era5_prev3d_rain": int(prepared["rain_era5_city_prev3d_mm"].notna().sum()),
        "date_year_disagrees_with_year_column": int((dates.notna() & dates.dt.year.ne(pd.to_numeric(raw["Year"], errors="coerce"))).sum()),
        "reference_point_lat_lon": [REFERENCE_LAT, REFERENCE_LON],
        "reference_point_source": "https://nominatim.openstreetmap.org/search?q=Ho+Chi+Minh+City%2C+Vietnam&format=jsonv2&limit=1",
        "rain_source_url": url,
        "rain_response_metadata": response_metadata,
        "rain_limit": "Single city-reference ERA5 grid point, not observation-site rainfall; no location coordinates in source table.",
    }
    (OUT / "enrichment_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: audit[k] for k in list(audit)[:6]}, indent=2))


if __name__ == "__main__":
    main()
