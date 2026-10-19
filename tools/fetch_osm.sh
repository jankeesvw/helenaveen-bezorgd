#!/usr/bin/env bash
# Haalt de OpenStreetMap-data van Helenaveen op via Overpass en schrijft data/osm.json.
set -euo pipefail
cd "$(dirname "$0")/.."
BBOX="51.3850,5.8990,51.4160,5.9320"
Q="[out:json][timeout:60];
(
  way[\"highway\"]($BBOX);
  way[\"waterway\"]($BBOX);
  way[\"natural\"=\"water\"]($BBOX);
  relation[\"natural\"=\"water\"]($BBOX);
  way[\"building\"]($BBOX);
  way[\"landuse\"]($BBOX);
  way[\"natural\"~\"wood|tree_row|scrub|heath|wetland\"]($BBOX);
  node[\"natural\"=\"tree\"]($BBOX);
  way[\"leisure\"]($BBOX);
  node[\"addr:street\"=\"Koolweg\"]($BBOX);
  way[\"addr:street\"=\"Koolweg\"]($BBOX);
);
out body geom;"
curl -sf -A "helenaveen-bezorgd/1.0" --data-urlencode "data=$Q" https://overpass-api.de/api/interpreter -o data/osm.json
echo "data/osm.json: $(jq '.elements | length' data/osm.json) elementen"

# benoemde plekken (bedrijven, boerderijen, monumenten) voor de naambordjes en de weetjes
P="[out:json][timeout:60];
(
  nwr[name][shop]($BBOX); nwr[name][amenity]($BBOX); nwr[name][office]($BBOX); nwr[name][craft]($BBOX);
  nwr[name][tourism]($BBOX); nwr[name][historic]($BBOX); nwr[name][building]($BBOX);
);
out center tags;"
curl -sf -A "helenaveen-bezorgd/1.0" --data-urlencode "data=$P" https://overpass-api.de/api/interpreter -o data/poi.json
echo "data/poi.json: $(jq '.elements | length' data/poi.json) plekken"
