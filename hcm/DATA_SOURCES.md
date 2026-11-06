# Enrichment source decisions

## Selected sources

- Flood coordinates: official `HCMC_Floods_BDD.gpkg`, 425 points, EPSG:9210, DataSuds file ID 50143, MD5 `1f618063abb8344471af01b3780c0519`.
- Surface water: official `HCMC_water.gpkg`, 2,430 polygons, DataSuds file ID 50145, MD5 `0590430eca0e97e1fe2ec6b7af3e2eb5`. Distance is computed in the point layer's metre-based CRS.
- Rainfall: NASA POWER `IMERG_PRECTOT` V07, native 0.1-degree grid, daily UTC. One request is made per occupied native cell and cached.
- Elevation: Copernicus DEM GLO-90 2021, 90 m, accessed through Open-Meteo's elevation endpoint.

The older `era5_hcm_reference_daily.csv` contains a one-point city reference series. It is retained only for provenance of the earlier pilot and is not an input to the current enriched table.

## Why these are preferable

The published point layer preserves the authors' manual geolocation and stated spatial precision; automated street-name geocoding would add avoidable ambiguity. IMERG is satellite/gauge precipitation at about 10 km rather than one shared city value. The water layer comes from the same research package, so distances are reproducible without a live Overpass query.

## Important limits

- A 0.1-degree rain cell is not a rain gauge and cannot resolve street-scale convection.
- IMERG daily values are UTC, while event dates were reported in Vietnam local time and have no event hour.
- GLO-90 vertical accuracy and urban surface representation limit interpretation of small elevation differences in flat HCMC.
- Water distance depends on the published layer's completeness and polygon geometry.
- Two Bà Rịa-Vũng Tàu observations are outside the water layer bounding box. Their distances are missing rather than being incorrectly measured to the dataset edge. One in-extent value above 5 km is retained with a review flag.
- Sixty-three observations have no exact date. Their rainfall is intentionally left missing; deriving a day from `Year` would fabricate data.

## References

- DataSuds flood dataset: https://doi.org/10.23708/8Y16HU
- NASA POWER IMERG documentation: https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/
- NASA POWER Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- Open-Meteo Elevation API / Copernicus DEM GLO-90: https://open-meteo.com/en/docs/elevation-api
- Copernicus DEM citation DOI: https://doi.org/10.5270/ESA-c5d3d65

## Licence discrepancy

The current DataSuds landing page states CC BY-NC 4.0, while the deposited README states CC BY 4.0. This repository applies the more restrictive CC BY-NC 4.0 condition pending clarification from the data owner. This discrepancy must not be silently resolved in favour of the less restrictive licence.
