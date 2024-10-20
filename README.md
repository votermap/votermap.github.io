# Election Comparison Map
This repository contains the code for an interactive map of US Presidential Election results. This README will explain some of the choices made on the map and serve as a guide for anyone who wants to replicate it.

## Environment
You'll need `geopandas` and it's dependencies in your python environment, as well as a few system packages:
- `tippecanoe` for creating map tiles (this also installs `tile-join`)
- `mbtileserver` for serving map tiles locally

## Get Data
Most of the data on this map comes from `redistrictingdatahub.org` (no affiliation). The Redistricting Data Hub distributes US election results disaggregated to the Census Block level, which we can use more or less directly to generate the points that we'd show at the highest zoom levels on the map, one dot = one vote.

Collecting the data is a bit manual: download the data set at each of the links at the bottom of this README, extract the CSV file or SHP directory, and put them in the `data` folder. See links at bottom of this README. 

## Handle CA/DC/PA
The Redistricting Data Hub provides block-level disaggregted election results for both 2016 and 2020 for most states, but CA/DC/PA don't have 2016 block-level shapefiles. 2020 block-level data is available, which includes voting-age population per block, but we'll have to disaggregate the 2016 election results onto these blocks manually. This can be done using election results data from the University of Florida's election lab, which provides precinct boundaries and vote totals for CA/DC/PA for 2016. This is done by running python `ingest_DC_PA_CA.py` - more details of how we do this disaggregation can be found in that file.

## Process Each State

Run `python ingest_state.py <state_abbr>` for each state, or run `./all_states.sh` to run it for all states. The ingest_state script will do the following:

1. Open the 2016 block-level result shapefile, which includes 2020 census block IDs and boundaries as well as election results
2. Open the 2020 block-level result CSV, which includes 2020 census block IDs and results, but no boundaries
3. Join the two datasets to associate 2020 results with block boundaries
4. Round as below
5. Save the results as `geojson/<state_abbr>_<year>_points.geojson`
6. Run tippecanoe to create `tiles/<state_abbr>_<year>.mbtiles`

### Rounding
The disaggregated results contain a block's share of the vote for a precinct, which is a decimal number. We can only show an integer number of dots, so we need to round to the nearest whole number. We round using a -stochastic- process: A block with 0.1 votes has a 10% chance of showing a single vote.
TODO: Is there somewhere on the map where this makes a visible difference?

## Join the Tiles 
```
tile-join --no-tile-size-limit -o all.mbtiles tiles/*
```

## Serve the map
At this point, we can display the map using this `.mbtiles` file and the `mbtileserver` package. Run `mbtileserver -d . -p 1234` (this port is hard-coded) to serve the map tiles. In another terminal, run `python -m http.server 8080` (or any port - this one doesn't matter) to serve the map UI at http://localhost:8080/map.html. The reason we need to run a second server for the static HTML page is that we request the base map tiles from Stadia, which requires an API key for requests that aren't from `localhost`. 

## Deploy the tiles
Rather than actually hosting an instance of `mbtileserver`, the tiles are hosted for produciton in an S3 bucket. We'll have to extract every tile from the `.mbtiles` archive and push it to S3 with `python tiler2.py`.

## Raw Data Sources
Every downloaded zip should be placed in the `data` directory and then extracted.
```
Contains 2020 block-level disaggregated results for the entire US
https://redistrictingdatahub.org/dataset/2020-presidential-democratic-republican-vote-share-on-nationwide-2020-census-blocks/

Contains 2016 election results disagreggated onto 2020 blocks for all states besides CA/DC/PA
https://redistrictingdatahub.org/dataset/2016-alabama-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-alaska-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-arizona-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-arkansas-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-colorado-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-connecticut-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-delaware-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-florida-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-georgia-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-hawaii-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-idaho-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-illinois-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-indiana-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-iowa-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-kansas-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-kentucky-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-louisiana-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-maine-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-maryland-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-massachusetts-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-michigan-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-minnesota-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-mississippi-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-missouri-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-montana-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-nebraska-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-nevada-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-new-hampshire-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-new-jersey-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-new-mexico-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-new-york-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-north-carolina-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-north-dakota-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-ohio-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-oklahoma-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-oregon-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-rhode-island-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-south-carolina-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-south-dakota-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-tennessee-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-texas-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-utah-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-vermont-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-virginia-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-washington-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-west-virginia-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-wisconsin-general-election-results-disaggregated-to-2020-census-blocks/
https://redistrictingdatahub.org/dataset/2016-wyoming-general-election-results-disaggregated-to-2020-census-blocks/

# CA/DC/PA precint-level data which we'll have to disaggregate ourselves
https://election.lab.ufl.edu/dataset/pa-2016-precinct-level-election-results/
https://election.lab.ufl.edu/dataset/pa-2020-precinct-level-election-results/
https://election.lab.ufl.edu/dataset/dc-2020-precinct-level-election-results/
https://election.lab.ufl.edu/dataset/dc-2016-precinct-level-election-results/
https://election.lab.ufl.edu/dataset/ca-2016-precinct-level-election-results/
https://election.lab.ufl.edu/dataset/ca-2020-precinct-level-election-results/


# CA/DC/PA 2020 blocks (from https://www2.census.gov/geo/tiger/TIGER_RD18/STATE/)
https://www2.census.gov/geo/tiger/TIGER_RD18/STATE/11_DISTRICT_OF_COLUMBIA/11/tl_rd22_11_tabblock20.zip
https://www2.census.gov/geo/tiger/TIGER_RD18/STATE/42_PENNSYLVANIA/42/tl_rd22_42_tabblock20.zip
https://www2.census.gov/geo/tiger/TIGER_RD18/STATE/06_CALIFORNIA/06/tl_rd22_06_tabblock20.zip
```

All data displayed on the map was accessed on October 15-17, 2024. 
