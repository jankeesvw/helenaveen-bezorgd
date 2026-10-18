#!/usr/bin/env python3
"""Haalt de actuele PDOK-luchtfoto van de kaart op (0,5 m per pixel) en plakt die tot data/luchtfoto.jpg."""
import io, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
X0, Y0, X1, Y1 = 190716, 377549, 192843, 380634   # RD New, zelfde vak als 3DBAG
RES, TILE = 0.5, 2000                              # meter per pixel, pixels per tegel
W, H = round((X1 - X0) / RES), round((Y1 - Y0) / RES)
out = Image.new('RGB', (W, H))
for ty in range(0, H, TILE):
    for tx in range(0, W, TILE):
        w, h = min(TILE, W - tx), min(TILE, H - ty)
        bx0, bx1 = X0 + tx * RES, X0 + (tx + w) * RES
        by1, by0 = Y1 - ty * RES, Y1 - (ty + h) * RES
        url = ('https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0?service=WMS&version=1.3.0&request=GetMap'
               f'&layers=Actueel_orthoHR&styles=&crs=EPSG:28992&bbox={bx0},{by0},{bx1},{by1}&width={w}&height={h}&format=image/jpeg')
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'tour-helenaveen/1.0'}), timeout=120) as r:
            out.paste(Image.open(io.BytesIO(r.read())).convert('RGB'), (tx, ty))
        print(f'tegel {tx},{ty} ({w}x{h})', flush=True)
out.save(ROOT / 'data' / 'luchtfoto.jpg', quality=88)
(ROOT / 'data' / 'luchtfoto.txt').write_text(f'{X0} {Y0} {X1} {Y1} {RES}\n')
print('data/luchtfoto.jpg', W, 'x', H)
