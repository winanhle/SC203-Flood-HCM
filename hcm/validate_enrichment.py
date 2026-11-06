"""Validate enriched outputs; use --online to independently re-query NASA POWER."""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
EXPECTED = {
    "rows": 425, "dated": 362, "numeric": 147, "classes": 168,
    "numeric_with_rain": 123, "classes_with_rain": 139, "water_distance": 423,
}


def query_imerg(row: pd.Series) -> dict:
    day = pd.Timestamp(row.date_iso)
    params = {
        "parameters": "IMERG_PRECTOT", "community": "AG",
        "longitude": row.longitude, "latitude": row.latitude,
        "start": (day - pd.Timedelta(days=7)).strftime("%Y%m%d"),
        "end": day.strftime("%Y%m%d"), "format": "JSON", "time-standard": "UTC",
    }
    url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "SC203-enrichment-validation/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    data = pd.read_csv(DATA / "flood_observations_enriched.csv")
    original = pd.read_csv(HERE / "Flood_event_locations.tab", sep="\t")
    rain = data.rain_imerg_site_day_mm.notna()
    checks = {
        "row_count": len(data) == EXPECTED["rows"],
        "unique_objectid": not data.OBJECTID.duplicated().any(),
        "original_row_order_preserved": data.OBJECTID.tolist() == original.OBJECTID.tolist(),
        "dated_rows": data.date_iso.notna().sum() == EXPECTED["dated"],
        "numeric_target_rows": data.water_height_max_m.notna().sum() == EXPECTED["numeric"],
        "class_target_rows": data.depth_class_label.notna().sum() == EXPECTED["classes"],
        "coordinate_coverage": data[["latitude", "longitude"]].notna().all(axis=1).all(),
        "elevation_coverage": data.elevation_copernicus_glo90_m.notna().all(),
        "water_distance_valid_rows": data.distance_to_water_m.notna().sum() == EXPECTED["water_distance"],
        "water_extent_flags": data.water_distance_quality_flag.eq("outside_water_layer_bbox").sum() == 2,
        "outside_extent_distance_is_missing": data.loc[data.water_distance_quality_flag.eq("outside_water_layer_bbox"), "distance_to_water_m"].isna().all(),
        "rain_exactly_on_dated_rows": rain.equals(data.date_iso.notna()),
        "all_rain_windows_complete": data.loc[rain, [
            "rain_imerg_site_day_mm", "rain_imerg_site_prev1d_mm",
            "rain_imerg_site_prev3d_mm", "rain_imerg_site_prev7d_mm",
        ]].notna().all().all(),
        "numeric_with_rain": (data.water_height_max_m.notna() & rain).sum() == EXPECTED["numeric_with_rain"],
        "classes_with_rain": (data.depth_class_label.notna() & rain).sum() == EXPECTED["classes_with_rain"],
        "nonnegative_physical_features": data[[
            "distance_to_water_m", "elevation_copernicus_glo90_m",
            "rain_imerg_site_day_mm", "rain_imerg_site_prev1d_mm",
            "rain_imerg_site_prev3d_mm", "rain_imerg_site_prev7d_mm",
        ]].min().min() >= 0,
    }
    online_records = []
    if args.online:
        sample = data.loc[rain].drop_duplicates([
            "imerg_grid_latitude", "imerg_grid_longitude"
        ]).head(5)
        for _, row in sample.iterrows():
            payload = query_imerg(row)
            values = payload["properties"]["parameter"]["IMERG_PRECTOT"]
            series = pd.Series({pd.to_datetime(k): v for k, v in values.items()})
            day = pd.Timestamp(row.date_iso)
            expected = {
                "day": series.loc[day],
                "prev1d": series.loc[day-pd.Timedelta(days=1):day-pd.Timedelta(days=1)].sum(),
                "prev3d": series.loc[day-pd.Timedelta(days=3):day-pd.Timedelta(days=1)].sum(),
                "prev7d": series.loc[day-pd.Timedelta(days=7):day-pd.Timedelta(days=1)].sum(),
            }
            actual = {
                "day": row.rain_imerg_site_day_mm,
                "prev1d": row.rain_imerg_site_prev1d_mm,
                "prev3d": row.rain_imerg_site_prev3d_mm,
                "prev7d": row.rain_imerg_site_prev7d_mm,
            }
            matched = all(abs(expected[k] - actual[k]) < 1e-9 for k in expected)
            online_records.append({
                "OBJECTID": int(row.OBJECTID), "source": payload["header"]["sources"],
                "api_version": payload["header"]["api"]["version"],
                "time_standard": payload["header"]["time_standard"], "matched": matched,
            })
        checks["online_nasa_power_samples"] = len(online_records) == 5 and all(x["matched"] for x in online_records)
    checks = {key: bool(value) for key, value in checks.items()}
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks, "online_samples": online_records,
    }
    output = HERE / "results" / "enrichment_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
