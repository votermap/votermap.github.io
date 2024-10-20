from sys import argv
import geopandas as gpd
import pandas as pd
import numpy as np
import os
import shapely
import json

def open_state_shapefile(state_abbr):
    dirs = [x for x in os.listdir('data') if os.path.isdir(os.path.join('data', x))]
    state_dir = [d for d in dirs if d.lower().startswith(state_abbr.lower())][0]
    if not state_dir:
        raise FileNotFoundError(f"No directory found for state {state_abbr} in data/")
    state_path = os.path.join('data', state_dir)
    shapefile = next((f for f in os.listdir(state_path) if f.endswith('.shp')), None)
    if not shapefile:
        raise FileNotFoundError(f"No .shp file found in data/{state_dir}/")
    shapefile_path = os.path.join(state_path, shapefile)
    gdf = gpd.read_file(shapefile_path)
    return gdf

def stochastic_round(df, col, name):
    frac_part = df[col] - df[col].astype(int)
    random_values = np.random.random(len(df))
    df[name] = df[col].astype(int) + (random_values < frac_part).astype(int)
    return df

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

    df.rename(columns={
        col1: rename_map[cand1],
        col2: rename_map[cand2]
    }, inplace=True)

    for column in rename_map.values():
        df = stochastic_round(df, column, column)
    df = stochastic_round(df, 'Other', 'Other')

    relevant_cols = ['GEOID20', 'geometry', 'Other'] + list(rename_map.values())
    return df[relevant_cols]

def draw_dots(gdf, columns):
    for column in columns:
        name = f"{column}_points"
        gdf[name] = gdf.sample_points(gdf[column])
        print(f'Drew dots for {column}')

def create_point_features(gdf, columns):
    features = []
    for column in columns:
        points = gdf[f"{column}_points"]
        for point_or_collection in points:
            if isinstance(point_or_collection, shapely.geometry.Point):
                features.append({
                    "type": "Feature",
                    "geometry": point_or_collection.__geo_interface__,
                    "properties": {"category": column}
                })
            else:
                for point in point_or_collection.geoms:
                    features.append({
                        "type": "Feature",
                        "geometry": point.__geo_interface__,
                        "properties": {"category": column}
                    })
    return features

def save_geojson(features, filename):
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    path = os.path.join('geojson', filename)
    with open(path, 'w') as f:
        json.dump(geojson, f)
    print(f"Saved {path}")

def ingest(state_abbr):
    if os.path.exists(f'geojson/{state_abbr}_2020_points.geojson') and os.path.exists(f'geojson/{state_abbr}_2016_points.geojson'):
        print(f"geojson/{state_abbr}_2020_points.geojson and geojson/{state_abbr}_2016_points.geojson both exist, skipping")
        return

    state_gdf_2016 = open_state_shapefile(state_abbr)
    national_df_2020 = pd.read_csv('data/national_block_2020_pres_results/national_block_2020_pres_results.csv', dtype={'GEOID20': str})

    state_df_2020 = national_df_2020[national_df_2020['STATEAB'] == state_abbr]
    state_gdf_2020 = gpd.GeoDataFrame(national_df_2020.merge(state_gdf_2016[['GEOID20', 'geometry']], on='GEOID20', how='inner'))

    state_gdf_2020 = prep_df(state_gdf_2020, 'G20PRE', {"BID": "Biden", "TRU": "Trump"})
    state_gdf_2016 = prep_df(state_gdf_2016, 'G16PRE', {"CLI": "Clinton", "TRU": "Trump"})

    draw_dots(state_gdf_2020, ["Biden", "Trump", "Other"])
    draw_dots(state_gdf_2016, ["Clinton", "Trump", "Other"])

    points_2020 = create_point_features(state_gdf_2020, ["Biden", "Trump", "Other"])
    save_geojson(points_2020, f"{state_abbr}_2020_points.geojson")
    points_2016 = create_point_features(state_gdf_2016, ["Clinton", "Trump", "Other"])
    save_geojson(points_2016, f"{state_abbr}_2016_points.geojson")

def tile(state_abbr):
    tile_paths = [
        f"tiles/{state_abbr}_2020.mbtiles",
        f"tiles/{state_abbr}_2016.mbtiles"
    ]

    if all(os.path.exists(path) for path in tile_paths):
        print(f"tiles/{state_abbr}_2020.mbtiles and tiles/{state_abbr}_2016.mbtiles both exist, skipping")
        return
    
    for year in ["2020", "2016"]:
        # There are two ways that dots are 'dropped':

        # 1) Tippecanoe's standard rate reduction, which keeps 40% of features when you go up one zoom level
        # This is governed by the --baze-zoom ("level you have to zoom in, in order to see all the dots") flag

        # 2) Especially-dense-dot removal: when dots are too close together to be visibly distinguished, tippecanoe drops some of them
        # This is governed by --gamma, which means the -root- to reduce by. The default is 2, which means "keep the square root of the number of dots"
        # Our dots are low-opacity, so we are okay with more overlap than the default to show dots on top of each other in "purple" areas, so we use --gamma=1.5
        # There's no particular reason for 1.5 other than "I want to step away from the defaults in the direction of 'more dots'"
        cmd = f"tippecanoe -o tiles/{state_abbr}_{year}.mbtiles --layer=election_results_{year} -z13 --no-tile-size-limit --no-feature-limit --base-zoom=9 --gamma=1.5 geojson/{state_abbr}_{year}_points.geojson"
        os.system(cmd)

def main():
    if not os.path.exists('geojson'):
        os.makedirs('geojson')  
    if len(argv) > 1:
        ingest(argv[1])
        tile(argv[1])
    else:
        print("Please provide a state abbreviation as an argument.")

if __name__ == "__main__":
    main()