# HCMC flood-depth pilot — leakage-aware evaluation

Adapted from the supplied Berlin Phase 3 RF notebook: notebook50b59dca3c.ipynb.
Executed locally, cell by cell in Python. Kaggle execution has not been performed in this run.

## Run

Open HCMC_Method2_RF.ipynb. On Kaggle, attach Flood_event_locations.tab or enable Internet for the public download. CPU is sufficient. Run all cells.

## Added data for the next experiment

Run `python prepare_hcm_data.py` to rebuild `data/flood_observations_enriched.csv` from the unchanged original table and the Open-Meteo ERA5 archive. The companion `data/era5_hcm_reference_daily.csv` stores the daily series; `data/enrichment_audit.json` records the exact request and response metadata.

| Coverage | Rows |
|---|---:|
| Original observations | 425 |
| Numeric upper-depth target | 147 |
| Known depth-class label | 168 |
| Additional class-only observations | 21 |
| Parseable observation date with ERA5 daily rain | 362 |

Added columns are `date_iso`, `water_height_max_m`, `depth_class_label`, `rain_era5_city_day_mm`, `rain_era5_city_prev3d_mm`, and `rain_reference`. The preceding-three-day rainfall excludes the observation day. Blank targets remain blank.

Rain is from **one city-reference ERA5 grid point** at 10.7737261° N, 106.7166008° E, in the Asia/Bangkok daily time zone. It is a coarse exploratory weather covariate, not rainfall at each flood location. The source table has no latitude or longitude, so geocoding and site-specific rain, elevation, and river distance are still needed before testing H1. The existing pilot metrics below were not rerun with these new columns.

Weather source: [Open-Meteo Historical Weather API, ERA5 model](https://open-meteo.com/en/docs/historical-weather-api). Reference coordinate: [OpenStreetMap Nominatim city search](https://nominatim.openstreetmap.org/search?q=Ho+Chi+Minh+City%2C+Vietnam&format=jsonv2&limit=1). One observation has a parsed date whose year disagrees with the separate `Year` column; the table preserves both values for review.

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

The transitive grouping creates 10 components. Sharing a date links observations from different locations, and a large flood report can therefore join many locations into one component. Location and source links can extend that component further. This explains why the largest component contains 117 of 147 rows (79.6%).

| Test fold | Train rows | Test rows | Baseline MAE | RF MAE | RF + cause MAE | Baseline RMSE | RF RMSE | RF + cause RMSE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 30 | 117 | 0.4039 | 0.4317 | 0.4285 | 0.4280 | 0.5107 | 0.4964 |
| 1 | 135 | 12 | 0.2124 | 0.2758 | 0.4929 | 0.2194 | 0.2781 | 0.4954 |
| 2 | 138 | 9 | 1.2103 | 1.1891 | 1.1689 | 1.7094 | 1.6956 | 1.6691 |
| 3 | 142 | 5 | 0.1256 | 0.1500 | 0.1240 | 0.2249 | 0.2312 | 0.2253 |
| 4 | 143 | 4 | 0.3482 | 0.3882 | 0.3938 | 0.4334 | 0.4667 | 0.4889 |

Errors are in metres. The pooled MAE above weights rows, so fold 0 contributes 117/147 of its row-level errors; it is largely a reflection of that one component rather than a stable estimate across independent events. Fold 2 also has much higher error despite only nine test rows. Full-precision values are in `results/fold_metrics.csv`; row-level predictions are in `results/out_of_fold_predictions.csv`.

## Limits

This is a retrospective severity pilot among reported floods. It does not model flood occurrence or provide a physical rainfall forecast. The feature set has no rainfall, elevation or river-distance measurements, so it does not test the proposed H1 comparison. Adding reported Cause assumes it is known at prediction time. Grouped evaluation cannot remove newspaper selection bias or verify event identities.
The 147 available upper endpoints include four values of 3 m; these are retained as reported and can strongly affect errors. Missing endpoints are not zero. Treat these scores as unstable pilot evidence. Scores do not establish transfer from Berlin and cannot be directly compared to Berlin model accuracy.

## Next experiment

Geocode the observations, join daily rainfall, and derive elevation and distance to the nearest river or canal. Then compare rainfall-only, rainfall plus historical context, and rainfall plus historical and spatial predictors on the same grouped folds. A separate depth-class classifier could use observations without a numeric upper endpoint.

## Supplied Berlin notebooks

Phase 3 RF has real-data outputs (full-feature test R2 about 0.129). Phase 4 U-Net ran one epoch on eight real-data training patches; test R2 about -8.42. These are existing outputs in the supplied notebooks, not reruns during this task. The U-Net result demonstrates execution, not validated predictive quality.

## Sources and license

HCMC: Hardy, Sebastien; Radziute, Gintare (2026), Historical database of urban flooding in Ho Chi Minh City, Vietnam (2002–2026), DataSuds V1, https://doi.org/10.23708/8Y16HU . CC BY-NC 4.0: https://creativecommons.org/licenses/by-nc/4.0/ . Included Flood_event_locations.tab is unmodified; SHA256 is recorded in data_audit.json.
Berlin code: https://github.com/omarseleem92/Machine_learning_for_urban_flooding . Paper: https://doi.org/10.5194/nhess-23-809-2023 .

Generated adaptation and explanatory text were prepared with ChatGPT; metrics are from executed code, not invented.
