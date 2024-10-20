#!/bin/bash

set -e

states=(
    "AL" "AK" "AZ" "AR" "CO" "CT" "DE" "FL" "GA" 
    "HI" "ID" "IL" "IN" "IA" "KS" "KY" "LA" "ME" "MD" 
    "MA" "MI" "MN" "MS" "MO" "MT" "NE" "NV" "NH" "NJ" 
    "NM" "NY" "NC" "ND" "OH" "OK" "OR" "RI" "SC" 
    "SD" "TN" "TX" "UT" "VT" "VA" "WA" "WV" "WI" "WY"
)

for state in "${states[@]}"
do
    echo "Processing $state..."
    python ingest_state.py "$state"
    echo "Finished processing $state"
    echo "------------------------"
done

python ingest_DC_PA_CA.py

echo "All states processed."

