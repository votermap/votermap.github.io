import os
import requests
from urllib.parse import urljoin
import concurrent.futures
import argparse
import boto3

BASE_URL = "http://localhost:7800/services/all/tiles/{z}/{x}/{y}.pbf"
OUTPUT_DIR = "tiles/static"
S3_BUCKET = 'resultmap'

# Initialize S3 client
s3 = boto3.client('s3')

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def download_tile(z, x, y):
    print(f"Downloading tile: {z}/{x}/{y}")
    url = BASE_URL.format(z=z, x=x, y=y)
    
    for attempt in range(3):
        response = requests.get(url)
        print(response)
        
        if response.status_code == 200:
            # Local file storage
            output_path = os.path.join(OUTPUT_DIR, str(z), str(x))
            os.makedirs(output_path, exist_ok=True)
            local_file_path = os.path.join(output_path, f"{y}.pbf")
            
            with open(local_file_path, "wb") as f:
                f.write(response.content)
            
            # S3 storage
            s3_key = f"tiles/{z}/{x}/{y}.pbf"
            s3.upload_file(local_file_path, S3_BUCKET, s3_key)
            
            print(f"Downloaded and uploaded tile: {z}/{x}/{y}")
            return
        elif response.status_code == 204:
            print(f"Tile {z}/{x}/{y} is empty")
            return
        else:
            print(f"Failed to download tile: {z}/{x}/{y}. Attempt {attempt + 1} of 3")
            if attempt == 2:
                print(f"All attempts failed for tile: {z}/{x}/{y}")

def generate_tile_list(min_zoom, max_zoom):
    tiles = []
    for z in range(min_zoom, max_zoom + 1):
        for x in range(2**z):
            for y in range(2**z):
                tiles.append((z, x, y))
    return tiles

def main(min_zoom, max_zoom, num_workers):
    list = generate_tile_list(min_zoom, max_zoom)
    for tile in list:
        download_tile(*tile)
    # tiles = generate_tile_list(min_zoom, max_zoom)
    
    # with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
    #     executor.map(lambda t: download_tile(*t), tiles)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate static .pbf files from mbtiles")
    parser.add_argument("--min-zoom", "-z", type=int, default=0, help="Minimum zoom level")
    parser.add_argument("--max-zoom", "-Z", type=int, default=13, help="Maximum zoom level")
    parser.add_argument("--threads", "-t", type=int, required=False, default=4, help="Number of worker threads")
    
    args = parser.parse_args()
    main(args.min_zoom, args.max_zoom, args.threads)
