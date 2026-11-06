"""Build reproducible physical covariates for the HCMC flood observations."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd

HERE = Path(__file__).resolve().parent
ORIGINAL, OUT = HERE / "Flood_event_locations.tab", HERE / "data"
SOURCE, CACHE = OUT / "source", OUT / "cache" / "era5_land"
POINTS, WATER = SOURCE / "HCMC_Floods_BDD.gpkg", SOURCE / "HCMC_water.gpkg"
SOURCE_FILES = {
    POINTS: (50143, "1f618063abb8344471af01b3780c0519"),
    WATER: (50145, "0590430eca0e97e1fe2ec6b7af3e2eb5"),
}
VALID_CLASSES = {"Low", "Moderate", "Heavy", "Severe"}
USER_AGENT = "SC203-HCMC-flood-research/2.0 (academic reproducible pipeline)"


def fetch_json(url: str, timeout: int = 180, attempts: int = 4):
    last_error = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                payload = json.load(response)
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(payload.get("reason", "API error"))
            return payload
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Request failed after {attempts} attempts: {url}") from last_error


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_point_alignment(points: gpd.GeoDataFrame, tabular: pd.DataFrame) -> None:
    """Prove row alignment using all shared attributes, not only the duplicate Obs_id."""
    text_fields = {
        "Obs_id": "Obs_id", "Location_name": "Location name",
        "Location_type": "Location type", "District_mentioned": "District mentioned",
        "Ward": "Ward/Phường", "Commune": "Commune/Xã",
        "Current_admin_unit": "Current admin unit", "Province": "Province",
        "Depth_class": "Depth class", "Cause": "Cause", "Impact_type": "Impact type",
        "Source_id": "Source id", "Source_type": "Source type",
        "Spatial_precision": "Spatial precision", "Geocoding_method": "Geocoding method",
        "Observation_notes": "Observation notes",
    }
    for geo_col, tab_col in text_fields.items():
        left = points[geo_col].fillna("").astype(str).str.strip().replace("<Nul>", "").reset_index(drop=True)
        right = tabular[tab_col].fillna("").astype(str).str.strip().replace("<Nul>", "").reset_index(drop=True)
        if not left.equals(right):
            mismatch = (left != right).to_numpy().nonzero()[0][:5].tolist()
            raise ValueError(f"Point/tab alignment failed for {geo_col}: rows {mismatch}")
    numeric_fields = {
        "Year": "Year", "Water_height_min_cm": "Water height min (cm)",
        "Water_height_max_cm": "Water height max (cm)", "Duration_hours": "Duration (h)",
    }
    for geo_col, tab_col in numeric_fields.items():
        left = pd.to_numeric(points[geo_col].astype(str).str.replace(",", ".", regex=False), errors="coerce").astype("float64").reset_index(drop=True)
        right = pd.to_numeric(tabular[tab_col].astype(str).str.replace(",", ".", regex=False), errors="coerce").astype("float64").reset_index(drop=True)
        if not left.equals(right):
            raise ValueError(f"Point/tab numeric alignment failed for {geo_col}")
    left_date = pd.to_datetime(points["Date"], errors="coerce", utc=True).dt.tz_localize(None).dt.normalize().astype("datetime64[ns]").reset_index(drop=True)
    right_date = pd.to_datetime(tabular["Date"], format="%d/%m/%Y", errors="coerce").dt.normalize().astype("datetime64[ns]").reset_index(drop=True)
    if not left_date.equals(right_date):
        raise ValueError("Point/tab date alignment failed")


def ensure_sources() -> None:
    SOURCE.mkdir(parents=True, exist_ok=True)
    for path, (file_id, expected) in SOURCE_FILES.items():
        if not path.exists():
            req = urllib.request.Request(
                f"https://dataverse.ird.fr/api/access/datafile/{file_id}",
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=180) as response:
                path.write_bytes(response.read())
        if md5(path) != expected:
            raise ValueError(f"Checksum mismatch for {path.name}")


def spatial_features() -> pd.DataFrame:
    points_native = gpd.read_file(POINTS)
    source_rows = pd.read_csv(ORIGINAL, sep="\t", dtype=str, keep_default_na=False)
    if len(points_native) != 425:
        raise ValueError("Official point layer should contain 425 rows")
    validate_point_alignment(points_native, source_rows)
    # Obs_id has one duplicate in the published source. OBJECTID is the stable key.
    points_native["OBJECTID"] = source_rows["OBJECTID"].tolist()
    points_wgs = points_native.to_crs(4326)
    result = pd.DataFrame({
        "OBJECTID": points_wgs["OBJECTID"],
        "latitude": points_wgs.geometry.y,
        "longitude": points_wgs.geometry.x,
    })
    water = gpd.read_file(WATER).to_crs(points_native.crs)
    xmin, ymin, xmax, ymax = water.total_bounds
    result["water_layer_extent_covered"] = (
        points_native.geometry.x.between(xmin, xmax)
        & points_native.geometry.y.between(ymin, ymax)
    ).to_numpy()
    nearest = gpd.sjoin_nearest(
        points_native[["OBJECTID", "geometry"]], water[["geometry"]],
        how="left", distance_col="distance_to_water_m",
    )
    distance = nearest.groupby("OBJECTID", as_index=False)["distance_to_water_m"].min()
    result = result.merge(distance, on="OBJECTID", validate="one_to_one")
    result["water_distance_quality_flag"] = "ok"
    result.loc[~result.water_layer_extent_covered, "water_distance_quality_flag"] = "outside_water_layer_bbox"
    result.loc[result.water_layer_extent_covered & result.distance_to_water_m.gt(5000), "water_distance_quality_flag"] = "review_gt_5km"
    result.loc[~result.water_layer_extent_covered, "distance_to_water_m"] = pd.NA
    result[["latitude", "longitude"]] = result[["latitude", "longitude"]].round(6)
    result["distance_to_water_m"] = result["distance_to_water_m"].round(3)
    return result


def add_elevation(spatial: pd.DataFrame) -> pd.DataFrame:
    values = []
    for start in range(0, len(spatial), 100):
        batch = spatial.iloc[start:start + 100]
        params = {
            "latitude": ",".join(batch.latitude.map(lambda x: f"{x:.6f}")),
            "longitude": ",".join(batch.longitude.map(lambda x: f"{x:.6f}")),
        }
        url = "https://api.open-meteo.com/v1/elevation?" + urllib.parse.urlencode(params, safe=",")
        values.extend(fetch_json(url)["elevation"])
    spatial = spatial.copy()
    spatial["elevation_copernicus_glo90_m"] = values
    return spatial


def month_weather(rows: pd.DataFrame, period: pd.Period) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE / f"{period}.json"
    expected_ids = rows.OBJECTID.tolist()
    if cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("obs_ids") == expected_ids:
            return cached["responses"]
    params = {
        "latitude": ",".join(rows.latitude.map(lambda x: f"{x:.6f}")),
        "longitude": ",".join(rows.longitude.map(lambda x: f"{x:.6f}")),
        "start_date": (period.start_time - pd.Timedelta(days=7)).strftime("%Y-%m-%d"),
        "end_date": period.end_time.strftime("%Y-%m-%d"),
        "daily": "precipitation_sum", "models": "era5_land",
        "timezone": "Asia/Bangkok", "cell_selection": "nearest",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params, safe=",")
    payload = fetch_json(url, timeout=300)
    responses = payload if isinstance(payload, list) else [payload]
    if len(responses) != len(rows):
        raise ValueError(f"Weather API returned {len(responses)} locations for {len(rows)} rows")
    cache_path.write_text(json.dumps({
        "obs_ids": expected_ids, "request_url": url, "responses": responses,
    }), encoding="utf-8")
    return responses


def site_rainfall(prepared: pd.DataFrame) -> pd.DataFrame:
    dated = prepared.loc[prepared.date_iso.ne(""), [
        "OBJECTID", "date_iso", "latitude", "longitude"
    ]].copy()
    dated["period"] = pd.to_datetime(dated.date_iso).dt.to_period("M")
    records = []
    for period, rows in dated.groupby("period", sort=True):
        rows = rows.sort_values("OBJECTID").reset_index(drop=True)
        for (_, row), response in zip(rows.iterrows(), month_weather(rows, period)):
            rain = pd.Series(response["daily"]["precipitation_sum"],
                             index=pd.to_datetime(response["daily"]["time"]), dtype="float64")
            day = pd.Timestamp(row.date_iso)
            records.append({
                "OBJECTID": row.OBJECTID,
                "rain_era5_land_site_day_mm": rain.get(day),
                "rain_era5_land_site_prev1d_mm": rain.loc[day-pd.Timedelta(days=1):day-pd.Timedelta(days=1)].sum(min_count=1),
                "rain_era5_land_site_prev3d_mm": rain.loc[day-pd.Timedelta(days=3):day-pd.Timedelta(days=1)].sum(min_count=3),
                "rain_era5_land_site_prev7d_mm": rain.loc[day-pd.Timedelta(days=7):day-pd.Timedelta(days=1)].sum(min_count=7),
                "rain_grid_latitude": response.get("latitude"),
                "rain_grid_longitude": response.get("longitude"),
            })
    return pd.DataFrame(records)


def imerg_rainfall(prepared: pd.DataFrame) -> pd.DataFrame:
    """Join NASA IMERG V07 daily rain, requesting each native 0.1-degree cell once."""
    cache_dir = OUT / "cache" / "nasa_power_imerg"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dated = prepared.loc[prepared.date_iso.ne(""), [
        "OBJECTID", "date_iso", "latitude", "longitude"
    ]].copy()
    # IMERG cell centers are at x.x5 on the native 0.1-degree grid.
    dated["imerg_grid_latitude"] = dated.latitude.map(lambda x: round(math.floor(x * 10) / 10 + 0.05, 2))
    dated["imerg_grid_longitude"] = dated.longitude.map(lambda x: round(math.floor(x * 10) / 10 + 0.05, 2))
    first = (pd.to_datetime(dated.date_iso).min() - pd.Timedelta(days=7)).strftime("%Y%m%d")
    last = pd.to_datetime(dated.date_iso).max().strftime("%Y%m%d")
    records = []
    for (lat, lon), rows in dated.groupby(["imerg_grid_latitude", "imerg_grid_longitude"]):
        cache_path = cache_dir / f"{lat:.2f}_{lon:.2f}_{first}_{last}.json"
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            params = {
                "parameters": "IMERG_PRECTOT", "community": "AG",
                "longitude": lon, "latitude": lat, "start": first, "end": last,
                "format": "JSON", "time-standard": "UTC",
            }
            url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + urllib.parse.urlencode(params)
            payload = fetch_json(url, timeout=120)
            cache_path.write_text(json.dumps(payload), encoding="utf-8")
        values = payload["properties"]["parameter"]["IMERG_PRECTOT"]
        rain = pd.Series({pd.to_datetime(k): v for k, v in values.items()}, dtype="float64")
        rain = rain.mask(rain.eq(-999.0))
        for row in rows.itertuples():
            day = pd.Timestamp(row.date_iso)
            records.append({
                "OBJECTID": row.OBJECTID,
                "rain_imerg_site_day_mm": round(float(rain.get(day)), 2),
                "rain_imerg_site_prev1d_mm": round(float(rain.loc[day-pd.Timedelta(days=1):day-pd.Timedelta(days=1)].sum(min_count=1)), 2),
                "rain_imerg_site_prev3d_mm": round(float(rain.loc[day-pd.Timedelta(days=3):day-pd.Timedelta(days=1)].sum(min_count=3)), 2),
                "rain_imerg_site_prev7d_mm": round(float(rain.loc[day-pd.Timedelta(days=7):day-pd.Timedelta(days=1)].sum(min_count=7)), 2),
                "imerg_grid_latitude": lat,
                "imerg_grid_longitude": lon,
            })
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weather-source", choices=["imerg", "era5_land", "none"], default="imerg")
    parser.add_argument("--skip-weather", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    ensure_sources()
    raw = pd.read_csv(ORIGINAL, sep="\t", dtype=str, keep_default_na=False)
    dates = pd.to_datetime(raw.Date, format="%d/%m/%Y", errors="coerce")
    prepared = raw.copy()
    prepared["date_iso"] = dates.dt.strftime("%Y-%m-%d").fillna("")
    prepared["water_height_max_m"] = pd.to_numeric(raw["Water height max (cm)"], errors="coerce") / 100
    prepared["depth_class_label"] = raw["Depth class"].where(raw["Depth class"].isin(VALID_CLASSES), "")
    spatial = add_elevation(spatial_features())
    spatial.to_csv(OUT / "spatial_features.csv", index=False, encoding="utf-8-sig")
    prepared = prepared.merge(spatial, on="OBJECTID", how="left", validate="one_to_one")
    source = "none" if args.skip_weather else args.weather_source
    if source != "none":
        rain = imerg_rainfall(prepared) if source == "imerg" else site_rainfall(prepared)
        rain.to_csv(OUT / f"{source}_site_event_rain.csv", index=False, encoding="utf-8-sig")
        prepared = prepared.merge(rain, on="OBJECTID", how="left", validate="one_to_one")
    assert len(prepared) == len(raw)
    assert prepared["OBJECTID"].tolist() == raw["OBJECTID"].tolist()
    enriched_path = OUT / "flood_observations_enriched.csv"
    prepared.to_csv(enriched_path, index=False, encoding="utf-8-sig")
    rain_col = "rain_imerg_site_day_mm" if source == "imerg" else "rain_era5_land_site_day_mm"
    has_rain = prepared[rain_col].notna() if rain_col in prepared else pd.Series(False, index=prepared.index)
    audit = {
        "original_rows": len(raw),
        "numeric_depth_rows": int(prepared.water_height_max_m.notna().sum()),
        "known_depth_class_rows": int(prepared.depth_class_label.ne("").sum()),
        "class_only_extra_rows": int((prepared.water_height_max_m.isna() & prepared.depth_class_label.ne("")).sum()),
        "rows_with_parseable_date": int(dates.notna().sum()),
        "rows_with_official_coordinates": int(prepared.latitude.notna().sum()),
        "rows_with_elevation": int(prepared.elevation_copernicus_glo90_m.notna().sum()),
        "rows_with_water_distance": int(prepared.distance_to_water_m.notna().sum()),
        "rows_outside_water_layer_bbox": int(prepared.water_distance_quality_flag.eq("outside_water_layer_bbox").sum()),
        "rows_with_water_distance_review_flag": int(prepared.water_distance_quality_flag.eq("review_gt_5km").sum()),
        "weather_source_selected": source,
        "rows_with_site_rain": int(has_rain.sum()),
        "numeric_depth_rows_with_date_and_site_rain": int((prepared.water_height_max_m.notna() & has_rain).sum()),
        "depth_class_rows_with_date_and_site_rain": int((prepared.depth_class_label.ne("") & has_rain).sum()),
        "dataset_doi": "https://doi.org/10.23708/8Y16HU",
        "point_layer": {"dataverse_file_id": 50143, "download_url": "https://dataverse.ird.fr/api/access/datafile/50143", "md5": SOURCE_FILES[POINTS][1], "crs": "EPSG:9210"},
        "water_layer": {"dataverse_file_id": 50145, "download_url": "https://dataverse.ird.fr/api/access/datafile/50145", "md5": SOURCE_FILES[WATER][1], "features": 2430},
        "elevation_source": {"description": "Copernicus DEM GLO-90 (2021), 90 m, through Open-Meteo Elevation API", "documentation": "https://open-meteo.com/en/docs/elevation-api", "doi": "https://doi.org/10.5270/ESA-c5d3d65"},
        "rain_source": {"description": "NASA POWER IMERG_PRECTOT V07, 0.1 degree (~10 km), UTC daily", "api_endpoint": "https://power.larc.nasa.gov/api/temporal/daily/point", "documentation": "https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/"} if source == "imerg" else {"description": "Open-Meteo Historical API; ERA5-Land, approx. 9 km; per-site nearest grid; Asia/Bangkok daily boundary", "documentation": "https://open-meteo.com/en/docs/historical-weather-api"},
        "rain_antecedent_definition": "prev1d/3d/7d exclude observation day",
        "alignment_check": "425 rows matched on date and all 21 shared non-geometry attributes; OBJECTID used as unique join key because Obs_id has one duplicate",
        "source_sha256": {POINTS.name: sha256(POINTS), WATER.name: sha256(WATER)},
        "output_sha256": {
            enriched_path.name: sha256(enriched_path),
            "spatial_features.csv": sha256(OUT / "spatial_features.csv"),
            f"{source}_site_event_rain.csv": sha256(OUT / f"{source}_site_event_rain.csv") if source != "none" else None,
        },
        "license_note": "Dataset landing page states CC BY-NC 4.0 while deposited README states CC BY 4.0; apply CC BY-NC 4.0 conservatively pending clarification.",
    }
    (OUT / "enrichment_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
