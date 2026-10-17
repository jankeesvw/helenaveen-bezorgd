#!/usr/bin/env python3
"""Haalt alle 3DBAG-panden binnen de kaart op en schrijft data/3dbag.json.

De API telt offsets vanaf 1, geeft soms minder panden terug dan gevraagd en heeft per pagina
een eigen transform. Daarom lopen we met overlap door de offsets, ontdubbelen we op id en
rekenen we de hoekpunten meteen om naar echte RD/NAP-coördinaten (meters).
"""
import json, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BBOX = (190716, 377549, 192843, 380634)  # RD New, ruim om de wereld van build.py
base = f"https://api.3dbag.nl/collections/pand/items?bbox={','.join(map(str, BBOX))}&limit=100"


def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'ape-helenaveen/1.0'}), timeout=60) as r:
                return json.load(r)
        except Exception as e:  # tijdelijke 500's van de API
            print('opnieuw:', e, flush=True); time.sleep(1 + attempt)
    raise RuntimeError(url)


features, seen, offset, matched = [], set(), 1, float("inf")
while offset < matched:
    page = get(f"{base}&offset={offset}")
    matched = page.get('numberMatched', 0)
    sc, tr = page['metadata']['transform']['scale'], page['metadata']['transform']['translate']
    for f in page['features']:
        if f['id'] in seen:
            continue
        seen.add(f['id'])
        f['vertices'] = [[round(v[i] * sc[i] + tr[i], 3) for i in range(3)] for v in f['vertices']]
        features.append(f)
    n = page.get('numberReturned', len(page['features']))
    print(f"offset {offset}: {n} terug, {len(features)} / {matched}", flush=True)
    offset += max(1, n - 3)
(ROOT / 'data' / '3dbag.json').write_text(json.dumps({'crs': 'EPSG:7415', 'features': features}))
