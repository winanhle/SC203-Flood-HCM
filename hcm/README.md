# HCMC flood-depth pilot — leakage-aware evaluation

Adapted from the supplied Berlin Phase 3 RF notebook: notebook50b59dca3c.ipynb.
Executed locally, cell by cell in Python. Kaggle execution has not been performed in this run.

## Run

Open HCMC_Method2_RF.ipynb. On Kaggle, attach Flood_event_locations.tab or enable Internet for the public download. CPU is sufficient. Run all cells.

## Added data for the next experiment

Run `python prepare_hcm_data.py` to rebuild `data/flood_observations_enriched.csv`. The pipeline uses the official published point layer rather than re-geocoding street names.

| Coverage | Rows |
|---|---:|
| Official coordinates and elevation | 425 |
| Valid water distance within published layer extent | 423 |
| Exact date and site-grid IMERG rain | 362 |
| Numeric target + site-grid rain | 123 |
| Class target + site-grid rain | 139 |
| Class target + spatial features (rain optional) | 168 |

Added physical columns include `latitude`, `longitude`, `elevation_copernicus_glo90_m`, `distance_to_water_m`, `rain_imerg_site_day_mm`, and antecedent 1/3/7-day rainfall. Antecedent sums exclude the observation day.

Two Bà Rịa-Vũng Tàu points fall outside the published water layer bounding box; their water distances are intentionally missing and flagged `outside_water_layer_bbox`. One in-extent distance above 5 km is flagged `review_gt_5km` for sensitivity analysis.

Rain is NASA GPM IMERG V07 `IMERG_PRECTOT`, requested through NASA POWER at each native 0.1-degree (about 10 km) cell represented by an observation. The 362 dated rows occupy 13 cells. IMERG daily values use UTC; because the source has dates but no event times, assignment near the 07:00 ICT UTC boundary is uncertain. Use same-day and antecedent features in sensitivity tests.

Coordinates and the 2,430-feature river/canal/water-body layer come from the same [DataSuds flood dataset](https://doi.org/10.23708/8Y16HU). Elevation comes from Copernicus DEM GLO-90 (90 m) through the [Open-Meteo Elevation API](https://open-meteo.com/en/docs/elevation-api). Rain methodology is documented by [NASA POWER](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/). GeoPackages are checksum-verified against DataSuds metadata.

Optional: `python prepare_hcm_data.py --weather-source era5_land` requests per-site ERA5-Land instead. `--weather-source none` rebuilds only spatial features. API responses are cached locally but the cache is not versioned.

`data/era5_hcm_reference_daily.csv` is retained as a legacy artifact from the earlier one-point experiment. It is not joined into the current enriched table and must not be used as the site-rainfall feature.

## What changed

- Replaced Berlin raster sampling with a reader for the unchanged HCMC table.
- Retained RandomForestRegressor, 10 trees, seed 42. Fits new models on HCMC.
- Features: year, month, location type, district, province; a separate variant adds known cause.
- Excluded depth-derived labels, impacts, free text, IDs and source from predictors.
- Target is the reported upper endpoint (cm / 100), not necessarily measured peak depth.
- Missing targets are excluded. Named location, source ID and parsed date are combined transitively into one group for evaluation.
- Compared against a training-mean dummy baseline on identical folds.

## Results

The table below is the current result to cite for this pilot. All models use the same five folds, with location, source and date links kept together. Lower MAE and RMSE are better; higher R² is better.

| Model | Inputs | n | MAE (m) | RMSE (m) | R² |
|---|---|---:|---:|---:|---:|
| Mean baseline | Training-fold mean | 147 | **0.4266** | **0.5792** | **−0.5220** |
| Random forest | Year, month, location type, district, province | 147 | 0.4546 | 0.6306 | −0.8044 |
| Random forest + cause | Above plus reported cause | 147 | 0.4678 | 0.6284 | −0.7919 |

Neither forest improves on the mean baseline. The earlier location-only R² of 0.7059 is superseded because its folds could share an event or source.

## Group balance

The transitive grouping creates 10 components. The largest holds 117 of 147 rows (79.6%), so the five test folds contain 117, 12, 9, 5 and 4 rows. These highly unequal folds make the pooled metrics sensitive to a single component. See `results/fold_metrics.csv` for each fold and `results/out_of_fold_predictions.csv` for row-level predictions.

## Limits

This is a retrospective severity pilot among reported floods. It does not model flood occurrence or provide a physical rainfall forecast. The feature set has no rainfall, elevation or river-distance measurements, so it does not test the proposed H1 comparison. Adding reported Cause assumes it is known at prediction time. Grouped evaluation cannot remove newspaper selection bias or verify event identities.
The 147 available upper endpoints include four values of 3 m; these are retained as reported and can strongly affect errors. Missing endpoints are not zero. Treat these scores as unstable pilot evidence. Scores do not establish transfer from Berlin and cannot be directly compared to Berlin model accuracy.

## Next experiment

Compare rainfall-only, rainfall plus historical context, and rainfall plus historical and spatial predictors on the same leakage-safe grouped folds. Run both regression (123 complete rain/target rows) and a separate depth-class classifier (139 complete rain/class rows; 168 rows for spatial-only classification). Do not infer event days from `Year`, and do not encode missing rainfall as zero.

## Supplied Berlin notebooks

Phase 3 RF has real-data outputs (full-feature test R2 about 0.129). Phase 4 U-Net ran one epoch on eight real-data training patches; test R2 about -8.42. These are existing outputs in the supplied notebooks, not reruns during this task. The U-Net result demonstrates execution, not validated predictive quality.

## Sources and license

HCMC: Hardy, Sebastien; Radziute, Gintare (2026), Historical database of urban flooding in Ho Chi Minh City, Vietnam (2002–2026), DataSuds V1, https://doi.org/10.23708/8Y16HU . CC BY-NC 4.0: https://creativecommons.org/licenses/by-nc/4.0/ . Included Flood_event_locations.tab is unmodified; SHA256 is recorded in data_audit.json.
Berlin code: https://github.com/omarseleem92/Machine_learning_for_urban_flooding . Paper: https://doi.org/10.5194/nhess-23-809-2023 .

Generated adaptation and explanatory text were prepared with ChatGPT; metrics are from executed code, not invented.
