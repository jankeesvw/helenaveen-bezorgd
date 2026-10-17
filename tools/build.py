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
SITE_URL = 'https://jankeesvw.github.io/ape-helenaveen/'
SOCIAL_META = (
    '<meta name="description" content="Rij met een groene Piaggio Ape van de Soemeersingel naar Koolweg 42 in Helenaveen, over de wortelbulten en langs de Helenavaart.">\n'
    '<meta property="og:type" content="website">\n'
    '<meta property="og:title" content="Met de Ape naar Koolweg 42">\n'
    '<meta property="og:description" content="Een 3D-ritje door Helenaveen op echte kaartdata: de Soemeersingel, de Helenavaart en de wortelbulten.">\n'
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

LAND_KIND = {'forest': 0, 'wood': 0, 'grass': 1, 'meadow': 1, 'farmland': 2, 'orchard': 3,
             'heath': 4, 'wetland': 5, 'scrub': 6, 'cemetery': 7, 'residential': 8,
             'farmyard': 9, 'plant_nursery': 10, 'park': 1, 'pitch': 11, 'playground': 9,
             'education': 8}

random.seed(42)


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
    for b in buildings:
        del b['a']

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
    trees = []  # (x, z, soort, schaal)  soort 0 = loof, 1 = den, 2 = berk, 3 = fruit
    tree_grid = Grid(10)
    def try_tree(x, z, kind, scale, road_margin=1.6, spacing=2.5):
        if not (BOUNDS[0] < x < BOUNDS[2] and BOUNDS[1] < z < BOUNDS[3]):
            return False
        if near_road(x, z, road_margin) or in_water(x, z, 0.8) or in_building(x, z, 1.5):
            return False
        for (tx, tz) in tree_grid.near(x, z):
            if math.hypot(tx - x, tz - z) < spacing:
                return False
        trees.append((x, z, kind, scale))
        tree_grid.add((x, z, x, z), (x, z))
        return True

    for e in els:
        t = e.get('tags', {})
        if e['type'] == 'node' and t.get('natural') == 'tree':
            x, z = proj(e['lat'], e['lon'])
            try_tree(x, z, 0, 1.0 + random.random() * 0.3)
    for e in els:
        t = e.get('tags', {})
        if e['type'] == 'way' and t.get('natural') == 'tree_row' and 'geometry' in e:
            pts = [proj(p['lat'], p['lon']) for p in e['geometry']]
            for i in range(len(pts) - 1):
                (ax, az), (bx, bz) = pts[i], pts[i + 1]
                L = math.hypot(bx - ax, bz - az)
                for s in range(int(L // 7) + 1):
                    f = s * 7 / max(L, 0.01)
                    try_tree(ax + (bx - ax) * f, az + (bz - az) * f, 0, 0.9 + random.random() * 0.3, 1.2)

    # laanbomen langs de singels en hoofdwegen
    lane_roads = {'Soemeersingel', 'Koolweg', 'Helenaveenseweg', 'Sevenumseweg', 'Kamp Mariaveen', 'Oude Peelstraat'}
    for r in roads:
        if r['s'] < 0 or names[r['s']] not in lane_roads:
            continue
        pts = road_pts(r)
        off = r['w'] / 2 + 2.6
        for i in range(len(pts) - 1):
            (ax, az), (bx, bz) = pts[i], pts[i + 1]
            L = math.hypot(bx - ax, bz - az)
            if L < 1:
                continue
            nx, nz = -(bz - az) / L, (bx - ax) / L
            s = random.random() * 6
            while s < L:
                f = s / L
                px, pz = ax + (bx - ax) * f, az + (bz - az) * f
                for side in (-1, 1):
                    if random.random() < 0.88:
                        try_tree(px + nx * off * side, pz + nz * off * side, 0, 0.95 + random.random() * 0.35, 1.8, 6)
                s += 11 + random.random() * 4

    # bos: dennen en berken in de Peel
    for pts in forest_polys:
        bb = bbox(pts)
        bb = (max(bb[0], BOUNDS[0]), max(bb[1], BOUNDS[1]), min(bb[2], BOUNDS[2]), min(bb[3], BOUNDS[3]))
        step = 8.5
        x = bb[0]
        while x < bb[2]:
            z = bb[1]
            while z < bb[3]:
                px, pz = x + random.uniform(-3, 3), z + random.uniform(-3, 3)
                if pip(px, pz, pts):
                    r = random.random()
                    kind = 1 if r < 0.45 else (2 if r < 0.75 else 0)
                    try_tree(px, pz, kind, 0.75 + random.random() * 0.5, 2.2, 3.5)
                z += step
            x += step
    for pts in orchard_polys:
        bb = bbox(pts)
        x = bb[0] + 2
        while x < bb[2]:
            z = bb[1] + 2
            while z < bb[3]:
                if pip(x, z, pts):
                    try_tree(x, z, 3, 0.8 + random.random() * 0.2, 1.5, 2.5)
                z += 5
            x += 4

    tree_flat = []
    for x, z, k, s in trees:
        tree_flat += [dm(x), dm(z), k, int(round(s * 100))]

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
    adj = {}
    for r in roads:
        if not r['d']:
            continue
        for i in range(len(r['n']) - 1):
            u, v = r['n'][i], r['n'][i + 1]
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
    }
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
          f"start {start}, poort ({gx:.0f},{gz:.0f}), doelgebouw {dest_building}")


if __name__ == '__main__':
    main()
