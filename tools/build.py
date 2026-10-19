#!/usr/bin/env python3
"""Zet data/osm.json om naar een compacte wereld en plakt die in src/game.html -> index.html.

Coordinaten: meters rond (51.400 N, 5.915 O), x naar het oosten, z naar het zuiden,
opgeslagen als gehele decimeters.
"""
import json, math, random, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAT0, LON0 = 51.400, 5.915
KX = math.cos(math.radians(LAT0)) * 111320
KZ = 110540
BOUNDS = (-1000.0, -1500.0, 1100.0, 1550.0)  # minx, minz, maxx, maxz

DEST_LATLON = (51.4054350, 5.9108390)  # Koolweg 42

# linkpreview (Telegram, WhatsApp, Slack) voor de GitHub Pages-versie
SITE_URL = 'https://jankeesvw.github.io/helenaveen-bezorgd/'
SOCIAL_META = (
    '<meta name="description" content="Bezorg met een Ape, Fiat 500, Kever of VW-busje zoveel mogelijk adressen in Helenaveen, over de wortelbulten en langs de Helenavaart, en laat je niet pakken door de politie.">\n'
    '<meta property="og:type" content="website">\n'
    '<meta property="og:title" content="Helenaveen bezorgd">\n'
    '<meta property="og:description" content="Bezorgen in 3D op echte kaartdata: pizza\'s, eieren, een taart of een aquarium, in vijf minuten zoveel mogelijk adressen, en rij je te hard dan komt de politie achter je aan.">\n'
    f'<meta property="og:url" content="{SITE_URL}">\n'
    f'<meta property="og:image" content="{SITE_URL}social.jpg">\n'
    '<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
    '<meta property="og:image:alt" content="Een groene Piaggio Ape op de Soemeersingel in Helenaveen">\n'
    '<meta name="twitter:card" content="summary_large_image">\n'
    f'<meta name="twitter:image" content="{SITE_URL}social.jpg">\n'
    '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%227%22 fill=%22%231d4f91%22/%3E%3Ctext x=%2216%22 y=%2224%22 font-family=%22Arial%22 font-weight=%22900%22 font-size=%2222%22 fill=%22%234f9a45%22 text-anchor=%22middle%22%3EA%3C/text%3E%3C/svg%3E">\n'
)
START_ADDRESS = 'Soemeersingel 25'     # hier staat de Ape bij de start

ROAD_W = {
    'tertiary': 6.0, 'secondary': 6.5, 'unclassified': 4.6, 'residential': 5.0,
    'living_street': 4.5, 'service': 3.4, 'track': 3.0, 'cycleway': 2.4,
    'footway': 1.8, 'path': 1.5, 'pedestrian': 3.5,
}
ROAD_KIND = {k: i for i, k in enumerate(ROAD_W)}
DRIVABLE = {'tertiary', 'secondary', 'unclassified', 'residential', 'living_street', 'service', 'track'}
# maximumsnelheid als OSM er geen maxspeed bij heeft
DEFAULT_LIMIT = {'tertiary': 50, 'secondary': 80, 'unclassified': 60, 'residential': 30, 'living_street': 30, 'service': 30, 'track': 60}

LAND_KIND = {'forest': 0, 'wood': 0, 'grass': 1, 'meadow': 1, 'farmland': 2, 'orchard': 3,
             'heath': 4, 'wetland': 5, 'scrub': 6, 'cemetery': 7, 'residential': 8,
             'farmyard': 9, 'plant_nursery': 10, 'park': 1, 'pitch': 11, 'playground': 9,
             'education': 8}

random.seed(42)


# soort en omschrijving van een benoemde plek uit OSM
POI_SUB = {('tourism', 'hotel'): 'hotel', ('amenity', 'restaurant'): 'eetcafé', ('amenity', 'fast_food'): 'cafetaria',
           ('tourism', 'guest_house'): 'pension', ('tourism', 'camp_site'): 'camping', ('tourism', 'caravan_site'): 'camperplaats',
           ('amenity', 'community_centre'): 'gemeenschapshuis', ('amenity', 'school'): 'basisschool', ('amenity', 'place_of_worship'): 'kerk'}


def poi_kind(t):
    subs = [v for (k, w), v in POI_SUB.items() if t.get(k) == w]
    if subs:
        return 'bedrijf', ' en '.join(subs)
    if t.get('name', '').lower().endswith('hoeve'):
        return 'hoeve', 'boerderij'
    if t.get('historic') in ('memorial', 'boundary_stone') or t.get('tourism') == 'artwork':
        return 'monument', {'boundary_stone': 'grenspaal'}.get(t.get('historic'), 'kunstwerk' if t.get('tourism') == 'artwork' else 'monument')
    return None, None


def proj(lat, lon):
    return ((lon - LON0) * KX, (LAT0 - lat) * KZ)


def dm(v):
    return int(round(v * 10))


def flat(pts):
    out = []
    for x, z in pts:
        out += [dm(x), dm(z)]
    return out


def bbox(pts):
    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    return min(xs), min(zs), max(xs), max(zs)


def in_bounds(bb, pad=0):
    return not (bb[2] < BOUNDS[0] - pad or bb[0] > BOUNDS[2] + pad or bb[3] < BOUNDS[1] - pad or bb[1] > BOUNDS[3] + pad)


def area(pts):
    a = 0
    for i in range(len(pts)):
        x1, z1 = pts[i]; x2, z2 = pts[(i + 1) % len(pts)]
        a += x1 * z2 - x2 * z1
    return a / 2


def pip(x, z, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, zi = pts[i]; xj, zj = pts[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
            inside = not inside
        j = i
    return inside


def seg_dist(px, pz, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    L = dx * dx + dz * dz
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (pz - az) * dz) / L))
    cx, cz = ax + t * dx, az + t * dz
    return math.hypot(px - cx, pz - cz), cx, cz, t


def simplify(pts, tol):
    if len(pts) < 4:
        return pts
    def rdp(a, b):
        ax, az = pts[a]; bx, bz = pts[b]
        best, idx = -1, -1
        for i in range(a + 1, b):
            d = seg_dist(pts[i][0], pts[i][1], ax, az, bx, bz)[0]
            if d > best:
                best, idx = d, i
        if best > tol:
            return rdp(a, idx)[:-1] + rdp(idx, b)
        return [pts[a], pts[b]]
    return rdp(0, len(pts) - 1)


def ring(geom):
    pts = [proj(p['lat'], p['lon']) for p in geom]
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.01:
        pts = pts[:-1]
    return pts


def hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def min_rect(pts):
    """Kleinste omsluitende rechthoek: (cx, cz, lengte, breedte, hoek van de lengteas)."""
    h = hull(pts)
    best = None
    for i in range(len(h)):
        x1, z1 = h[i]; x2, z2 = h[(i + 1) % len(h)]
        a = math.atan2(z2 - z1, x2 - x1)
        c, s = math.cos(a), math.sin(a)
        us = [x * c + z * s for x, z in h]
        vs = [-x * s + z * c for x, z in h]
        w, d = max(us) - min(us), max(vs) - min(vs)
        if best is None or w * d < best[0]:
            cu, cv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
            best = (w * d, cu * c - cv * s, cu * s + cv * c, w, d, a)
    _, cx, cz, w, d, a = best
    if d > w:
        w, d, a = d, w, a + math.pi / 2
    return cx, cz, w, d, a


class Grid:
    def __init__(self, cell):
        self.cell = cell; self.cells = {}

    def add(self, bb, item):
        c = self.cell
        for gx in range(int(math.floor(bb[0] / c)), int(math.floor(bb[2] / c)) + 1):
            for gz in range(int(math.floor(bb[1] / c)), int(math.floor(bb[3] / c)) + 1):
                self.cells.setdefault((gx, gz), []).append(item)

    def near(self, x, z):
        return self.cells.get((int(math.floor(x / self.cell)), int(math.floor(z / self.cell))), [])


def aerial_tiles(proj):
    """Knipt de luchtfoto in tegels (luchtfoto/hr en, op halve resolutie, luchtfoto/lr) en geeft de
    affiene afbeelding van wereldmeters naar fotopixels terug, zodat de game elke tegel op zijn plek legt."""
    from PIL import Image, ImageEnhance
    import bag3d
    from rd import rd_to_wgs
    X0, Y0, X1, Y1, RES = map(float, (ROOT / 'data' / 'luchtfoto.txt').read_text().split())
    # kleinste kwadraten over een raster van punten: wereld (x, z) -> pixel (u, v)
    rows = []
    for i in range(9):
        for j in range(9):
            xr, yr = X0 + (X1 - X0) * i / 8, Y0 + (Y1 - Y0) * j / 8
            x, z = proj(*rd_to_wgs(xr, yr)); x, z = x + bag3d.SHIFT[0], z + bag3d.SHIFT[1]
            rows.append((x, z, (xr - X0) / RES, (Y1 - yr) / RES))
    def fit(k):
        # normaalvergelijkingen voor [a b c]
        A = [[0.0] * 3 for _ in range(3)]; B = [0.0] * 3
        for r in rows:
            f = (r[0], r[1], 1.0)
            for m in range(3):
                B[m] += f[m] * r[k]
                for n in range(3):
                    A[m][n] += f[m] * f[n]
        for c in range(3):  # Gauss
            piv = max(range(c, 3), key=lambda q: abs(A[q][c])); A[c], A[piv] = A[piv], A[c]; B[c], B[piv] = B[piv], B[c]
            for q in range(c + 1, 3):
                t = A[q][c] / A[c][c]
                for n in range(c, 3):
                    A[q][n] -= t * A[c][n]
                B[q] -= t * B[c]
        x = [0.0] * 3
        for c in (2, 1, 0):
            x[c] = (B[c] - sum(A[c][n] * x[n] for n in range(c + 1, 3))) / A[c][c]
        return x
    aff = fit(2) + fit(3)
    err = max(abs(aff[0] * r[0] + aff[1] * r[1] + aff[2] - r[2]) + abs(aff[3] * r[0] + aff[4] * r[1] + aff[5] - r[3]) for r in rows)
    photo = Image.open(ROOT / 'data' / 'luchtfoto.jpg').convert('RGB')
    W, H = photo.size
    TILE, PAD = 1024, 2
    src = ROOT / 'data' / 'luchtfoto.jpg'
    for d in ('hr', 'lr'):
        (ROOT / 'luchtfoto' / d).mkdir(parents=True, exist_ok=True)
    stamp = ROOT / 'luchtfoto' / '.gemaakt'
    if not stamp.exists() or stamp.stat().st_mtime < src.stat().st_mtime:
        photo = ImageEnhance.Color(photo).enhance(1.25)  # voorjaarsfoto iets voller van kleur
        # de lage voorjaarszon geeft lange schaduwen in de foto: donkere tinten wat ophalen
        lut = [round(255 * (i / 255) ** 0.8) for i in range(256)]
        photo = photo.point(lut * 3)
        for r in range(math.ceil(H / TILE)):
            for c in range(math.ceil(W / TILE)):
                box = (max(0, c * TILE - PAD), max(0, r * TILE - PAD), min(W, (c + 1) * TILE + PAD), min(H, (r + 1) * TILE + PAD))
                t = photo.crop(box)
                t.save(ROOT / 'luchtfoto' / 'hr' / f'{c}_{r}.jpg', quality=80)
                t.resize((max(1, t.width // 2), max(1, t.height // 2)), Image.LANCZOS).save(ROOT / 'luchtfoto' / 'lr' / f'{c}_{r}.jpg', quality=78)
        stamp.touch()
    print(f'luchtfoto: {math.ceil(W / TILE)} x {math.ceil(H / TILE)} tegels, afwijking affien {err:.3f} px')
    return {'aff': [round(v, 7) for v in aff], 'W': W, 'H': H, 'tile': TILE, 'pad': PAD}


def main():
    raw = json.loads((ROOT / 'data' / 'osm.json').read_text())
    els = raw['elements']

    # ---------- wegen ----------
    node_idx, nodes = {}, []
    def nid(osm_id, x, z):
        if osm_id not in node_idx:
            node_idx[osm_id] = len(nodes); nodes.append((x, z))
        return node_idx[osm_id]

    names, name_idx = [], {}
    roads = []
    road_grid = Grid(30)
    for e in els:
        t = e.get('tags', {})
        hw = t.get('highway')
        if e['type'] != 'way' or hw not in ROAD_W or 'geometry' not in e:
            continue
        pts = [proj(p['lat'], p['lon']) for p in e['geometry']]
        bb = bbox(pts)
        if not in_bounds(bb, 50):
            continue
        idxs = [nid(n, *p) for n, p in zip(e['nodes'], pts)]
        nm = t.get('name', '')
        if nm and nm not in name_idx:
            name_idx[nm] = len(names); names.append(nm)
        w = ROAD_W[hw]
        try:
            w = max(w, min(8.0, float(t.get('width', '0').replace(',', '.'))))
        except ValueError:
            pass
        surf = t.get('surface', '')
        unpaved = 1 if (hw == 'track' and surf not in ('asphalt', 'concrete', 'paved', 'paving_stones')) or surf in ('dirt', 'grass', 'ground', 'gravel', 'fine_gravel', 'sand') else 0
        r = {'n': idxs, 'k': ROAD_KIND[hw], 'w': round(w, 1), 's': name_idx.get(nm, -1),
             'b': 1 if t.get('bridge') in ('yes', 'viaduct') else 0, 'u': unpaved,
             'd': 1 if hw in DRIVABLE else 0}
        if surf == 'wood':
            r['wd'] = 1
        if hw in DRIVABLE:
            ms = t.get('maxspeed', '').strip()
            r['v'] = int(ms) if ms.isdigit() else DEFAULT_LIMIT[hw]
        roads.append(r)
        ri = len(roads) - 1
        for i in range(len(pts) - 1):
            road_grid.add(bbox([pts[i], pts[i + 1]]), (ri, i))

    def road_pts(r):
        return [nodes[i] for i in r['n']]

    def near_road(x, z, margin):
        for ri, i in road_grid.near(x, z):
            r = roads[ri]
            a, b = nodes[r['n'][i]], nodes[r['n'][i + 1]]
            if seg_dist(x, z, a[0], a[1], b[0], b[1])[0] < r['w'] / 2 + margin:
                return True
        return False

    # ---------- water ----------
    water_polys = []  # {'o': outer, 'h': [holes]}
    water_grid = Grid(40)
    def add_water(outer, holes):
        outer = simplify(outer + [outer[0]], 0.4)[:-1]
        if len(outer) < 3 or not in_bounds(bbox(outer), 50):
            return
        holes = [simplify(h + [h[0]], 0.4)[:-1] for h in holes]
        water_polys.append({'o': outer, 'h': [h for h in holes if len(h) >= 3]})
        water_grid.add(bbox(outer), len(water_polys) - 1)

    def join_rings(ways):
        rings, open_ = [], [list(w) for w in ways]
        while open_:
            cur = open_.pop(0)
            changed = True
            while changed and math.hypot(cur[0][0] - cur[-1][0], cur[0][1] - cur[-1][1]) > 0.05:
                changed = False
                for k, w in enumerate(open_):
                    if math.hypot(cur[-1][0] - w[0][0], cur[-1][1] - w[0][1]) < 0.05:
                        cur += w[1:]; open_.pop(k); changed = True; break
                    if math.hypot(cur[-1][0] - w[-1][0], cur[-1][1] - w[-1][1]) < 0.05:
                        cur += list(reversed(w))[1:]; open_.pop(k); changed = True; break
            if math.hypot(cur[0][0] - cur[-1][0], cur[0][1] - cur[-1][1]) < 0.05:
                cur = cur[:-1]
            if len(cur) >= 3:
                rings.append(cur)
        return rings

    for e in els:
        t = e.get('tags', {})
        if t.get('natural') != 'water':
            continue
        if e['type'] == 'way' and 'geometry' in e:
            add_water(ring(e['geometry']), [])
        elif e['type'] == 'relation':
            outers = join_rings([[proj(p['lat'], p['lon']) for p in m['geometry']] for m in e['members'] if m['role'] == 'outer' and m.get('geometry')])
            inners = join_rings([[proj(p['lat'], p['lon']) for p in m['geometry']] for m in e['members'] if m['role'] == 'inner' and m.get('geometry')])
            for o in outers:
                add_water(o, [h for h in inners if pip(h[0][0], h[0][1], o)])

    WW = {'canal': 7.0, 'river': 8.0, 'stream': 2.6, 'ditch': 1.7, 'drain': 1.4}
    waterways = []
    ww_grid = Grid(40)
    for e in els:
        t = e.get('tags', {})
        ww = t.get('waterway')
        if e['type'] != 'way' or ww not in WW or 'geometry' not in e or t.get('tunnel'):
            continue
        pts = [proj(p['lat'], p['lon']) for p in e['geometry']]
        if not in_bounds(bbox(pts), 50):
            continue
        waterways.append({'p': pts, 'w': WW[ww]})
        for i in range(len(pts) - 1):
            ww_grid.add(bbox([pts[i], pts[i + 1]]), (len(waterways) - 1, i))

    def in_water(x, z, margin=0.0):
        for wi in water_grid.near(x, z):
            w = water_polys[wi]
            if pip(x, z, w['o']) and not any(pip(x, z, h) for h in w['h']):
                return True
        for wi, i in ww_grid.near(x, z):
            w = waterways[wi]
            a, b = w['p'][i], w['p'][i + 1]
            if seg_dist(x, z, a[0], a[1], b[0], b[1])[0] < w['w'] / 2 + margin:
                return True
        return False

    # ---------- gebouwen (3DBAG, met dakkleuren uit de luchtfoto) ----------
    import bag3d
    dest = proj(*DEST_LATLON)
    buildings, bld_shapes = bag3d.load(proj, in_bounds, bbox)
    bld_grid = Grid(30)
    for i, s in enumerate(bld_shapes):
        bld_grid.add(bbox(s), i)
    dest_building = next((i for i, b in enumerate(buildings) if 'Koolweg 42' in b['a']), None)
    start_fp = next(bld_shapes[i] for i, b in enumerate(buildings) if START_ADDRESS in b['a'])
    start_hint = (sum(p[0] for p in start_fp) / len(start_fp), sum(p[1] for p in start_fp) / len(start_fp))
    addr_lists = [b.pop('a') for b in buildings]

    def in_building(x, z, margin=0):
        for bi in bld_grid.near(x, z):
            s = bld_shapes[bi]
            bb = bbox(s)
            if bb[0] - margin <= x <= bb[2] + margin and bb[1] - margin <= z <= bb[3] + margin:
                if margin == 0:
                    if pip(x, z, s):
                        return True
                else:
                    return True
        return False

    # ---------- landgebruik ----------
    lands = []
    forest_polys, orchard_polys = [], []
    for e in els:
        t = e.get('tags', {})
        lu = t.get('landuse') or t.get('natural') or t.get('leisure')
        if e['type'] != 'way' or lu not in LAND_KIND or 'geometry' not in e:
            continue
        pts = ring(e['geometry'])
        if len(pts) < 3 or not in_bounds(bbox(pts)):
            continue
        pts = simplify(pts + [pts[0]], 0.8)[:-1]
        if len(pts) < 3:
            continue
        k = LAND_KIND[lu]
        lands.append({'p': flat(pts), 'k': k})
        if k == 0:
            forest_polys.append(pts)
        elif k == 3:
            orchard_polys.append(pts)

    # ---------- bomen ----------
    # Echte bomen uit het AHN (tools/ahn_trees.py): positie, hoogte en kruinstraal per boom.
    # Soort: dennen waar de kruin in het bos donker is op de luchtfoto, populieren als ze hoog en smal zijn.
    trees = []  # (x, z, soort, hoogte, kruinstraal)  soort 0 = loof, 1 = den, 2 = berk, 3 = fruit, 4 = populier
    def nearest_road(x, z):
        best = None
        for gx in (-1, 0, 1):
            for gz in (-1, 0, 1):
                for ri, i in road_grid.near(x + gx * 30, z + gz * 30):
                    r = roads[ri]; a, b = nodes[r['n'][i]], nodes[r['n'][i + 1]]
                    d, cx, cz, _ = seg_dist(x, z, a[0], a[1], b[0], b[1])
                    if best is None or d - r['w'] / 2 < best[0] - best[3] / 2:
                        best = (d, cx, cz, r['w'], r['d'])
        return best

    def place(x, z):
        """Stam van de weg en uit het water schuiven; None als hij nergens past."""
        for _ in range(16):
            nr = nearest_road(x, z)
            if nr and nr[0] < nr[3] / 2 + 0.6:          # op de weg: naar de berm
                d, cx, cz, w, _ = nr
                ux, uz = (x - cx, z - cz) if d > 0.05 else (1.0, 0.0)
                l = math.hypot(ux, uz); x, z = cx + ux / l * (w / 2 + 0.9), cz + uz / l * (w / 2 + 0.9)
                continue
            if in_water(x, z, 0.4):                    # boven het kanaal: richting de weg, de oever op
                if not nr:
                    return None
                ux, uz = nr[1] - x, nr[2] - z; l = math.hypot(ux, uz) or 1
                x, z = x + ux / l * 0.5, z + uz / l * 0.5
                continue
            return None if in_building(x, z) else (x, z)
        return None

    ahn_file = ROOT / 'data' / 'trees_ahn.json'
    ahn = json.loads(ahn_file.read_text()) if ahn_file.exists() else []
    import bag3d
    from rd import rd_to_wgs
    forest_lums = []
    for xr, yr, h, rad, lum in ahn:
        x, z = proj(*rd_to_wgs(xr, yr)); x, z = x + bag3d.SHIFT[0], z + bag3d.SHIFT[1]
        if any(pip(x, z, p) for p in forest_polys if bbox(p)[0] <= x <= bbox(p)[2]):
            forest_lums.append(lum)
    forest_lums.sort()
    dark = forest_lums[int(len(forest_lums) * 0.4)] if forest_lums else 0
    forest_bb = [(bbox(p), p) for p in forest_polys]
    orchard_bb = [(bbox(p), p) for p in orchard_polys]
    inside = lambda x, z, polys: any(bb[0] <= x <= bb[2] and bb[1] <= z <= bb[3] and pip(x, z, p) for bb, p in polys)
    for xr, yr, h, rad, lum in ahn:
        x, z = proj(*rd_to_wgs(xr, yr)); x, z = x + bag3d.SHIFT[0], z + bag3d.SHIFT[1]
        if not (BOUNDS[0] < x < BOUNDS[2] and BOUNDS[1] < z < BOUNDS[3]) or inside(x, z, orchard_bb):
            continue
        pos = place(x, z)
        if not pos:
            continue
        if inside(x, z, forest_bb):
            kind = 1 if lum <= dark else (2 if random.random() < 0.5 and h < 16 else 0)
        else:
            kind = 0  # langs de wegen en op de erven staan bijna alleen eiken
        trees.append((pos[0], pos[1], kind, h, rad))
    # boomgaarden: lage fruitbomen in rijen, uit OSM
    for pts in orchard_polys:
        bb = bbox(pts)
        x = bb[0] + 2
        while x < bb[2]:
            z = bb[1] + 2
            while z < bb[3]:
                if pip(x, z, pts) and not near_road(x, z, 1.5) and not in_water(x, z, 0.8) and not in_building(x, z, 1.5):
                    trees.append((x, z, 3, 3.0 + random.random() * 0.6, 1.3 + random.random() * 0.3))
                z += 5
            x += 4
    # bomen ver van de weg krijgen een vlag, zodat een telefoon er de helft van kan overslaan
    tree_grid = Grid(10)
    for t in trees:
        tree_grid.add((t[0], t[1], t[0], t[1]), (t[0], t[1]))

    tree_flat = []
    for x, z, k, h, rad in trees:
        nr = nearest_road(x, z)
        far = 0 if nr and nr[4] and nr[0] < 40 else 8
        tree_flat += [dm(x), dm(z), k | far, dm(h), dm(rad)]

    # ---------- start en bestemming ----------
    name_id = lambda n: name_idx[n]
    def nearest_on(name, x, z, drivable=True):
        best = None
        for ri, r in enumerate(roads):
            if r['s'] != name_id(name) or (drivable and not r['d']):
                continue
            pts = road_pts(r)
            for i in range(len(pts) - 1):
                d, cx, cz, tt = seg_dist(x, z, *pts[i], *pts[i + 1])
                if best is None or d < best[0]:
                    best = (d, cx, cz, ri, i, tt)
        return best

    _, gx, gz, gri, gi, gt = nearest_on('Koolweg', *dest)
    gate_node = roads[gri]['n'][gi if gt < 0.5 else gi + 1]

    # afstand over de weg naar de bestemming, om de Ape bij de start de goede kant op te zetten
    EDGE = 20  # zo ver van de rand houdt de kaart op (de game stopt je op 15 m)
    inside_map = lambda x, z, m: BOUNDS[0] + m < x < BOUNDS[2] - m and BOUNDS[1] + m < z < BOUNDS[3] - m
    adj = {}
    for r in roads:
        if not r['d']:
            continue
        for i in range(len(r['n']) - 1):
            u, v = r['n'][i], r['n'][i + 1]
            if not (inside_map(*nodes[u], EDGE) and inside_map(*nodes[v], EDGE)):
                continue  # de game rijdt en routeert niet over de rand van de kaart
            w = math.hypot(nodes[u][0] - nodes[v][0], nodes[u][1] - nodes[v][1])
            adj.setdefault(u, []).append((v, w)); adj.setdefault(v, []).append((u, w))
    import heapq
    dist = {gate_node: 0.0}; heap = [(0.0, gate_node)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj.get(u, []):
            if d + w < dist.get(v, 1e18):
                dist[v] = d + w; heapq.heappush(heap, (d + w, v))

    _, sx, sz, sri, si, _ = nearest_on('Soemeersingel', *start_hint)
    na, nb = roads[sri]['n'][si], roads[sri]['n'][si + 1]
    a, b = (nodes[nb], nodes[na]) if dist.get(na, 1e18) < dist.get(nb, 1e18) else (nodes[na], nodes[nb])
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz); dx, dz = dx / L, dz / L
    rx, rz = -dz, dx  # rechterkant van de rijrichting
    lane = roads[sri]['w'] / 4
    start = {'x': round(sx + rx * lane, 2), 'z': round(sz + rz * lane, 2), 'h': round(math.atan2(-dx, -dz), 4), 'label': START_ADDRESS}

    # adres-paaltje: tussen weg en huis
    vx, vz = dest[0] - gx, dest[1] - gz
    vl = math.hypot(vx, vz) or 1
    post = (gx + vx / vl * (roads[gri]['w'] / 2 + 1.8), gz + vz / vl * (roads[gri]['w'] / 2 + 1.8))

    # ---------- bezorgadressen: elk adres van een woning of bedrijf, met de plek op de weg ervoor ----------
    def nearest_any(x, z):
        best = None
        for ri, r in enumerate(roads):
            if not r['d'] or r['b']:
                continue
            pts = road_pts(r)
            for i in range(len(pts) - 1):
                d, cx, cz, tt = seg_dist(x, z, *pts[i], *pts[i + 1])
                if best is None or d < best[0]:
                    best = (d, cx, cz, ri, i, tt)
        return best

    addrs, seen = [], set()
    for bi, alist in enumerate(addr_lists):
        if not alist or buildings[bi]['k'] not in (0, 1):
            continue
        fp = bld_shapes[bi]
        cx, cz = sum(p[0] for p in fp) / len(fp), sum(p[1] for p in fp) / len(fp)
        for label in sorted(set(alist)):
            if label in seen:
                continue
            street = label.rsplit(' ', 1)[0]
            g = nearest_on(street, cx, cz) if street in name_idx else None
            if g is None or g[0] > 70 or roads[g[3]]['b']:
                g = nearest_any(cx, cz)
                if g is None or g[0] > 50:
                    continue
            d, ax, az, ri, i, tt = g
            ends = (i, i + 1) if tt < 0.5 else (i + 1, i)
            node = next((roads[ri]['n'][e] for e in ends if roads[ri]['n'][e] in dist), None)
            if node is None or not inside_map(ax, az, EDGE + 5):  # niet bereikbaar over de weg, of op de rand van de kaart
                continue
            ux, uz = cx - ax, cz - az
            ul = math.hypot(ux, uz) or 1
            off = min(roads[ri]['w'] / 2 + 1.8, ul * 0.6)
            px, pz = ax + ux / ul * off, az + uz / ul * off
            if in_building(px, pz):
                off = roads[ri]['w'] / 2 + 0.7
                px, pz = ax + ux / ul * off, az + uz / ul * off
            if not inside_map(px, pz, EDGE + 5):
                continue
            seen.add(label)
            addrs.append([label, dm(ax), dm(az), dm(px), dm(pz), node, dm(cx), dm(cz)])

    # benoemde plekken uit OSM (data/poi.json): bedrijven en boerderijen krijgen een naambordje, monumenten
    # kunnen een weetje dragen. Soort, omschrijving, plek en het adres als OSM het kent.
    pois = []
    poi_file = ROOT / 'data' / 'poi.json'
    for e in (json.loads(poi_file.read_text())['elements'] if poi_file.exists() else []):
        t = e['tags']; c = e.get('center') or e
        x, z = proj(c['lat'], c['lon'])
        if not inside_map(x, z, EDGE + 5):
            continue
        kind, sub = poi_kind(t)
        if not kind:
            continue
        label = f"{t['addr:street']} {t['addr:housenumber']}" if 'addr:street' in t and 'addr:housenumber' in t else ''
        # hetzelfde bedrijf als knoop en als gebouw (Oranjehoeve en Oranje Hoeve): één bordje, dat van het bedrijf
        twin = next((q for q in pois if math.hypot(q[3] - dm(x), q[4] - dm(z)) < 400 and q[0].replace(' ', '').lower()[:6] == t['name'].replace(' ', '').lower()[:6]), None)
        if twin:
            if twin[1] == 'hoeve' and kind == 'bedrijf':
                pois.remove(twin)
            else:
                continue
        pois.append([t['name'], kind, sub, dm(x), dm(z), label])

    world = {
        'bounds': [dm(v) for v in BOUNDS],
        'nodes': flat(nodes),
        'names': names,
        'roadKinds': list(ROAD_W),
        'roads': roads,
        'water': [{'o': flat(w['o']), 'h': [flat(h) for h in w['h']]} for w in water_polys],
        'waterways': [{'p': flat(w['p']), 'w': w['w']} for w in waterways],
        'buildings': buildings,
        'lands': lands,
        'trees': tree_flat,
        'start': start,
        'dest': {'addr': [dm(dest[0]), dm(dest[1])], 'gate': [dm(gx), dm(gz)], 'post': [dm(post[0]), dm(post[1])],
                 'node': gate_node, 'building': dest_building},
        'addrs': addrs,
        'pois': pois,
    }
    world['aerial'] = aerial_tiles(proj)
    js = json.dumps(world, separators=(',', ':'))
    (ROOT / 'data' / 'world.json').write_text(js)

    tpl = (ROOT / 'src' / 'game.html').read_text()
    page = tpl.replace('/*__WORLD__*/null', js)
    # artifact.html is de pagina zonder kop (de Artifact-viewer zet er zelf een omheen),
    # index.html is dezelfde pagina als los document voor de lokale webserver
    (ROOT / 'artifact.html').write_text(page)
    head = ('<!doctype html>\n<html lang="nl">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">\n'
            '<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="mobile-web-app-capable" content="yes">\n'
            '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n<meta name="theme-color" content="#1d4f91">\n'
            + SOCIAL_META
            + '</head>\n<body>\n')
    (ROOT / 'index.html').write_text(head + page + '\n</body>\n</html>\n')
    print(f"wegen {len(roads)}, knopen {len(nodes)}, water {len(water_polys)}+{len(waterways)}, gebouwen {len(buildings)}, "
          f"land {len(lands)}, bomen {len(trees)}, wereld {len(js)//1024} KB, "
          f"start {start}, poort ({gx:.0f},{gz:.0f}), doelgebouw {dest_building}, adressen {len(addrs)}")


if __name__ == '__main__':
    main()
