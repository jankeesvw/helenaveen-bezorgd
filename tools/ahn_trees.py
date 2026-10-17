#!/usr/bin/env python3
"""Echte bomen uit het AHN: kruintoppen zoeken in het verschil tussen oppervlakte- en maaiveldmodel.

Haalt het AHN (DSM en DTM, 0,5 m) van PDOK op, haalt de gebouwen uit 3DBAG eraf en zoekt in wat
overblijft naar lokale toppen. Per top: positie (RD), hoogte boven maaiveld en kruinstraal.
Schrijft data/trees_ahn.json. Vraagt numpy, scipy en Pillow.
"""
import io, json, math, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
X0, Y0, X1, Y1 = 190716, 377549, 192843, 380634   # zelfde vak als 3DBAG en de luchtfoto
RES, TILE = 0.5, 1000                              # meter per pixel, meter per tegel
W, H = round((X1 - X0) / RES), round((Y1 - Y0) / RES)
CACHE = ROOT / 'data' / 'ahn'
CACHE.mkdir(parents=True, exist_ok=True)


def raster(cov):
    out = np.full((H, W), np.nan, dtype=np.float32)
    for ty in range(Y1, Y0, -TILE):
        for tx in range(X0, X1, TILE):
            bx0, bx1, by1, by0 = tx, min(tx + TILE, X1), ty, max(ty - TILE, Y0)
            f = CACHE / f'{cov}_{bx0}_{by0}.tif'
            if not f.exists():
                url = ('https://service.pdok.nl/rws/ahn/wcs/v1_0?service=WCS&version=2.0.1&request=GetCoverage'
                       f'&coverageId={cov}&subset=x({bx0},{bx1})&subset=y({by0},{by1})&format=image/tiff')
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'ape-helenaveen/1.0'}), timeout=300) as r:
                    f.write_bytes(r.read())
                print('opgehaald', f.name, flush=True)
            a = np.array(Image.open(f), dtype=np.float32)
            a[(a > 1e30) | (a < -100)] = np.nan
            r0, c0 = round((Y1 - by1) / RES), round((bx0 - X0) / RES)
            out[r0:r0 + a.shape[0], c0:c0 + a.shape[1]] = a[:H - r0, :W - c0]
    return out


def to_px(x, y):
    return (x - X0) / RES, (Y1 - y) / RES


def main():
    dsm, dtm = raster('dsm_05m'), raster('dtm_05m')
    # maaiveld onder gebouwen en water ontbreekt: vul aan met het dichtstbijzijnde bekende maaiveld
    holes = np.isnan(dtm)
    idx = ndimage.distance_transform_edt(holes, return_distances=False, return_indices=True)
    dtm = dtm[tuple(idx)]
    chm = np.nan_to_num(dsm - dtm, nan=0.0)
    chm[chm < 0] = 0

    # gebouwen eraf (met een meter marge), anders worden daken en schoorstenen bomen
    mask = Image.new('L', (W, H), 0)
    draw = ImageDraw.Draw(mask)
    for f in json.loads((ROOT / 'data' / '3dbag.json').read_text())['features']:
        for o in f['CityObjects'].values():
            if o['type'] != 'Building':
                continue
            g = next((g for g in o.get('geometry', []) if str(g['lod']) == '0'), None)
            if g:
                draw.polygon([to_px(*f['vertices'][i][:2]) for i in g['boundaries'][0][0]], fill=255)
    bmask = ndimage.binary_dilation(np.array(mask) > 0, iterations=2)
    chm[bmask] = 0

    # kruintoppen: lokale maxima, met een groter venster naarmate de boom hoger is. AHN is in de winter
    # gevlogen, dus kale kruinen geven een rommelig beeld: eerst flink glad maken (1 m)
    sm = ndimage.gaussian_filter(chm, sigma=2.0)
    tops = np.zeros_like(sm, dtype=bool)
    for lo, hi, size in ((4, 8, 9), (8, 14, 13), (14, 20, 17), (20, 99, 21)):
        mx = ndimage.maximum_filter(sm, size=size)
        tops |= (sm >= lo) & (sm < hi) & (sm >= mx - 1e-4)
    lab, n = ndimage.label(tops)
    centres = ndimage.center_of_mass(tops, lab, range(1, n + 1))
    print(f'{n} kandidaat-toppen', flush=True)

    # kruinstraal: in acht richtingen tot de hoogte onder de helft zakt of een buurboom begint
    photo = Image.open(ROOT / 'data' / 'luchtfoto.jpg').convert('L')
    trees = []
    dirs = [(math.cos(a), math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    for cy, cx in centres:
        r, c = int(round(cy)), int(round(cx))
        h = float(sm[r, c])
        dist = []
        for dx, dy in dirs:
            d = 0.0
            prev = h
            while d < 8:
                d += RES
                rr, cc = int(round(r + dy * d / RES)), int(round(c + dx * d / RES))
                if not (0 <= rr < H and 0 <= cc < W):
                    break
                v = sm[rr, cc]
                if v < max(2.0, 0.4 * h) or v > prev + 1.5:
                    break
                prev = min(prev, v) if v < prev else prev
            dist.append(d)
        rad = float(np.median(dist))
        # palen, draden en losse takken hebben geen kruin
        win = chm[max(0, r - 3):r + 4, max(0, c - 3):c + 4]
        if rad < 1.0 or (win > 2).sum() < 10:
            continue
        x, y = X0 + cx * RES, Y1 - cy * RES
        # helderheid van de kruin op de luchtfoto: naaldbomen zijn donkerder
        lum = photo.getpixel((min(photo.width - 1, int(cx)), min(photo.height - 1, int(cy))))
        trees.append([round(x, 2), round(y, 2), round(h, 1), round(min(rad, 7.5), 1), int(lum)])
    # hogere bomen gaan voor: een lagere top vlak naast een hogere is dezelfde kruin
    trees.sort(key=lambda t: -t[2])
    kept, grid = [], {}
    for t in trees:
        dmin = min(7.0, max(2.5, 0.35 * t[2]))
        gx, gy = int(t[0] // 8), int(t[1] // 8)
        if any(math.hypot(o[0] - t[0], o[1] - t[1]) < dmin for i in (-1, 0, 1) for j in (-1, 0, 1) for o in grid.get((gx + i, gy + j), [])):
            continue
        kept.append(t); grid.setdefault((gx, gy), []).append(t)
    trees = kept
    (ROOT / 'data' / 'trees_ahn.json').write_text(json.dumps(trees))
    hs = sorted(t[2] for t in trees)
    print(f'{len(trees)} bomen, hoogte mediaan {hs[len(hs) // 2]} m, max {hs[-1]} m')


if __name__ == '__main__':
    main()
