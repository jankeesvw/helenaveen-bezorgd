#!/usr/bin/env python3
"""Haalt de BAG-verblijfsobjecten (adres, gebruiksdoel, pand) binnen de kaart op via de PDOK-WFS en schrijft data/bag_vbo.json."""
import json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BBOX = (190716, 377549, 192843, 380634)
out, start = [], 0
while True:
    url = ('https://service.pdok.nl/lv/bag/wfs/v2_0?service=WFS&version=2.0.0&request=GetFeature&typeName=bag:verblijfsobject'
           f'&bbox={",".join(map(str, BBOX))},urn:ogc:def:crs:EPSG::28992&outputFormat=application/json&count=1000&startIndex={start}')
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'ape-helenaveen/1.0'}), timeout=120) as r:
        page = json.load(r)
    feats = page.get('features', [])
    for f in feats:
        p = f['properties']
        out.append({k: p.get(k) for k in ('pandidentificatie', 'gebruiksdoel', 'openbare_ruimte', 'huisnummer', 'huisletter', 'bouwjaar', 'oppervlakte')})
    print(len(out), flush=True)
    if len(feats) < 1000:
        break
    start += 1000
(ROOT / 'data' / 'bag_vbo.json').write_text(json.dumps(out))
