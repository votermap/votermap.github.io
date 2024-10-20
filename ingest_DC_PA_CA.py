import geopandas as gpd
import pandas as pd
import numpy as np
import shapely
import os

from ingest_state import stochastic_round, draw_dots, create_point_features, save_geojson, tile

FIPS = {
    "DC": "11",
    "PA": "42",
    "CA": "06"
}

SUFFIX_MAP = {
    "BID": "Biden",
    "CLI": "Clinton",
    "TRU": "Trump",
}

def stochastic_round(df, col, name):
    frac_part = df[col] - df[col].astype(int)
    random_values = np.random.random(len(df))
    df[name] = df[col].astype(int) + (random_values < frac_part).astype(int)
    return df

# similar to in ingest_state, but we don't round here (precinct totals are already integers)
def prep_df(df, year_str, rename_map):
    cols = df.columns
    relevant_cols = [col for col in cols if year_str in col.upper()]

    cand1 = list(rename_map.keys())[0]
    cand2 = list(rename_map.keys())[1]

    col1 = [col for col in relevant_cols if cand1 in col.upper()][0]
    col2 = [col for col in relevant_cols if cand2 in col.upper()][0]
    other_cols = [col for col in relevant_cols if col not in [col1, col2]]

    df['Other'] = df[other_cols].sum(axis=1)
    df = df.drop(columns=other_cols)

    return df.rename(columns={
        col1: rename_map[cand1],
        col2: rename_map[cand2]
    })


def main():
    # This CSV has 2020 voting-age population by block 
    # it has 2020 election results too, but we won't use those - we'll use the same data source and disaggregation method for both years
    blocks_vap_path = "data/national_block_2020_pres_results/national_block_2020_pres_results.csv"
    blocks_vap_df = pd.read_csv(blocks_vap_path, dtype={'GEOID20': str})[['GEOID20','VAP_MOD']]

    for state_abbr, state_fips in FIPS.items():
        if os.path.exists(f"geojson/{state_abbr}_2020_points.geojson") and os.path.exists(f"geojson/{state_abbr}_2016_points.geojson"):
            print(f"Skipping {state_abbr} because we already have the points")
            continue
        print(f"Processing {state_abbr}")

        census_shapefile_path = f"data/tl_rd22_{state_fips}_tabblock20/tl_rd22_{state_fips}_tabblock20.shp"
        all_blocks_gdf = gpd.read_file(census_shapefile_path)
        all_blocks_gdf = all_blocks_gdf.merge(blocks_vap_df, on='GEOID20')

        # for both shapefiles, we'll use an equal-area projected geom for spatial joins, because we care about sensible overlap-area comparisons
        # for blocks we also use lat/lon (WGS84) geometry for generating geojson for tippecanoe
        all_blocks_gdf['projected_geom'] = all_blocks_gdf['geometry'].to_crs("EPSG:5070")
        all_blocks_gdf['wgs_geom'] = all_blocks_gdf['geometry'].to_crs("EPSG:4326")
        
        for year in [2016, 2020]:
            results_path = f"data/{state_abbr.lower()}_{year}/{state_abbr.lower()}_{year}.shp"
            precinct_results_gdf = gpd.read_file(results_path)
            precinct_results_gdf['projected_geom'] = precinct_results_gdf['geometry'].to_crs("EPSG:5070")
            precinct_results_gdf['precinct_id'] = precinct_results_gdf.index

            # for each block, find the precinct that it has maximum overlap with, using the projected geometry
            blocks_gdf = all_blocks_gdf.copy()
            blocks_gdf.set_geometry('projected_geom', inplace=True)
            precinct_results_gdf.set_geometry('projected_geom', inplace=True)

            # right df's primary geometry col will be lost in .sjoin, so we need to copy it
            precinct_results_gdf['precinct_projected_geom'] = precinct_results_gdf['projected_geom']

            blocks_gdf = gpd.sjoin(blocks_gdf, precinct_results_gdf, how='left', predicate='intersects')
            no_precinct_overlap = blocks_gdf[blocks_gdf['precinct_id'].isna()]
            blocks_gdf = blocks_gdf[~blocks_gdf['precinct_id'].isna()]

            # these are blocks we can't associate with any precinct
            if len(no_precinct_overlap) > 0:
                if year == 2020:
                    # for 2020, only zero-population blocks should have no precinct
                    assert no_precinct_overlap['VAP_MOD'].sum() == 0
                else:
                    # I'm not sure there is a way to tell if this is okay (e.g. if these blocks were unpopulated in 2016)
                    total_vap_2020 = no_precinct_overlap['VAP_MOD'].sum()
                    block_count = len(no_precinct_overlap)
                    print(f"{block_count} 2020 Census Blocks couldn't be matched to a 2016 precinct, accounting for {total_vap_2020} 2020 voters")

            # in CA, there are some blocks or precincts which are considered invalid geoms by gpd, .buffer(0) makes them valid
            blocks_gdf['projected_geom'] = blocks_gdf.projected_geom.buffer(0)
            blocks_gdf['precinct_projected_geom'] = blocks_gdf.precinct_projected_geom.buffer(0)
            blocks_gdf['intersection_area'] = blocks_gdf.projected_geom.intersection(blocks_gdf.precinct_projected_geom)
            blocks_gdf = blocks_gdf.sort_values('intersection_area', ascending=False).groupby('GEOID20').first().reset_index()

            if year == 2020:
                blocks_gdf = prep_df(blocks_gdf, "G20PRE", {"BID": "Biden", "TRU": "Trump"})
                candidates = ["Biden", "Trump", "Other"]
            else:
                blocks_gdf = prep_df(blocks_gdf, "G16PRE", {"CLI": "Clinton", "TRU": "Trump"})
                candidates = ["Clinton", "Trump", "Other"]

            blocks_gdf['precinct_vap'] = blocks_gdf.groupby('precinct_id')['VAP_MOD'].transform('sum')
            blocks_gdf['vap_share'] = blocks_gdf['VAP_MOD'] / blocks_gdf['precinct_vap']
            blocks_gdf['vap_share'] = blocks_gdf['vap_share'].fillna(0)
            
            for candidate in candidates:
                col_name = f"{candidate}_total"
                blocks_gdf[col_name] = blocks_gdf[candidate] * blocks_gdf['vap_share']
                stochastic_round(blocks_gdf, col_name, col_name)
                blocks_gdf = blocks_gdf.drop(columns=[candidate])
                blocks_gdf.rename(columns={col_name: candidate}, inplace=True)

            # drop all geoms besides wgs_geom, which we'll use for geojson output
            blocks_gdf = blocks_gdf.drop(columns=['projected_geom', 'precinct_projected_geom', 'intersection_area'])
            blocks_gdf.set_geometry('wgs_geom', inplace=True)
            draw_dots(blocks_gdf, candidates) 
            points = create_point_features(blocks_gdf, candidates)
            save_geojson(points, f"{state_abbr}_{year}_points.geojson")
    for state_abbr in FIPS.keys():
        if os.path.exists(f"tiles/{state_abbr}_2020.mbtiles") and os.path.exists(f"tiles/{state_abbr}_2016.mbtiles"):
            print(f"Skipping {state_abbr} because we already have the tiles")
            continue
        tile(state_abbr)

if __name__ == "__main__":
    main()
