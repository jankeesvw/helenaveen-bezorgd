"""3DBAG-panden omzetten naar gebouwen voor de spelwereld.

Per pand: het LoD2.2-model (dakvlakken en muren), omgerekend van RD/NAP naar de lokale meters
van de wereld en met de maaiveldhoogte op 0. Elk dakvlak krijgt de mediaankleur uit de
PDOK-luchtfoto, en de BAG bepaalt of het een woning, bedrijfspand, schuur, bijgebouw of kas is.
"""
import json, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageStat
from rd import rd_to_wgs

ROOT = Path(__file__).resolve().parent.parent
# OSM ligt gemiddeld zoveel naast 3DBAG; we schuiven 3DBAG mee zodat wegen en panden aansluiten
SHIFT = (-0.19, 0.22)
KIND = {'woon': 0, 'bedrijf': 1, 'schuur': 2, 'bijgebouw': 3, 'kas': 4}
WALL, ROOF = 1, 2


def load(proj, in_bounds, bbox):
    bag = json.loads((ROOT / 'data' / '3dbag.json').read_text())['features']
    vbo = json.loads((ROOT / 'data' / 'bag_vbo.json').read_text())
    uses, addr = {}, {}
    for v in vbo:
        uses.setdefault(v['pandidentificatie'], set()).update(g.strip() for g in (v['gebruiksdoel'] or '').split(','))
        addr.setdefault(v['pandidentificatie'], []).append(f"{v['openbare_ruimte']} {v['huisnummer']}{v['huisletter'] or ''}")
    X0, Y0, X1, Y1, RES = map(float, (ROOT / 'data' / 'luchtfoto.txt').read_text().split())
    photo = Image.open(ROOT / 'data' / 'luchtfoto.jpg')

    def to_local(x, y):
        lx, lz = proj(*rd_to_wgs(x, y))
        return lx + SHIFT[0], lz + SHIFT[1]

    def roof_colour(rd_ring):
        px = [((x - X0) / RES, (Y1 - y) / RES) for x, y in rd_ring]
        xs = [p[0] for p in px]; ys = [p[1] for p in px]
        x0, y0, x1, y1 = int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1
        if x1 - x0 < 2 or y1 - y0 < 2 or x0 < 0 or y0 < 0 or x1 > photo.width or y1 > photo.height:
            return None
        crop = photo.crop((x0, y0, x1, y1))
        mask = Image.new('L', crop.size, 0)
        ImageDraw.Draw(mask).polygon([(x - x0, y - y0) for x, y in px], fill=255)
        if sum(1 for m in mask.getdata() if m) < 6:
            return None
        r, g, b = ImageStat.Stat(crop, mask).median
        return (r << 16) | (g << 8) | b

    out, shapes = [], []
    for f in bag:
        objs = f['CityObjects']
        V = f['vertices']
        for oid, o in objs.items():
            if o['type'] != 'Building':
                continue
            a = o.get('attributes', {})
            pid = oid.split('.')[-1]
            fp_geom = next((g for g in o.get('geometry', []) if str(g['lod']) == '0'), None)
            if not fp_geom:
                continue
            fp = [to_local(*V[i][:2]) for i in fp_geom['boundaries'][0][0]]
            if not in_bounds(bbox(fp)):
                continue
            ground = a.get('b3_h_maaiveld')
            parts = [objs[c] for c in o.get('children', []) if c in objs]
            faces, used = [], {}
            for p in parts:
                geoms = {str(g['lod']): g for g in p.get('geometry', [])}
                g = geoms.get('2.2') or geoms.get('1.3') or geoms.get('1.2')
                if not g:
                    continue
                if g['type'] == 'Solid':
                    surfaces, values = g['boundaries'][0], g['semantics']['values'][0]
                else:
                    surfaces, values = g['boundaries'], g['semantics']['values']
                sem = g['semantics']['surfaces']
                for surf, si in zip(surfaces, values):
                    t = sem[si]['type'] if si is not None else 'WallSurface'
                    if t == 'GroundSurface':
                        continue
                    kind = ROOF if t == 'RoofSurface' else WALL
                    col = roof_colour([V[i][:2] for i in surf[0]]) if kind == ROOF else -1
                    rings = []
                    for ring in surf:
                        rr = []
                        for i in ring:
                            if i not in used:
                                used[i] = len(used)
                            rr.append(used[i])
                        rings.append(rr)
                    faces.append([kind, -1 if col is None else col] + rings)
            if not faces:
                continue
            if ground is None:
                ground = min(V[i][2] for i in used)
            # dakvlakken zonder bruikbare kleur krijgen de mediaan van de andere dakvlakken
            cols = sorted(fc[1] for fc in faces if fc[0] == ROOF and fc[1] >= 0)
            for fc in faces:
                if fc[0] == ROOF and fc[1] < 0:
                    fc[1] = cols[len(cols) // 2] if cols else 0x6a6560
            # hoekpunten relatief aan het eerste footprintpunt, in centimeters
            ox, oz = fp[0]
            verts = [None] * len(used)
            for i, k in used.items():
                lx, lz = to_local(*V[i][:2])
                h = max(0.0, V[i][2] - ground)
                verts[k] = (round((lx - ox) * 100), round(h * 100), round((lz - oz) * 100))
            doel = uses.get(pid, set())
            if a.get('b3_kas_warenhuis') is True:
                kind = 'kas'
            elif 'woonfunctie' in doel or 'logiesfunctie' in doel:
                kind = 'woon'
            elif doel:
                kind = 'bedrijf'
            else:
                kind = 'schuur' if (a.get('b3_opp_grond') or 0) > 120 else 'bijgebouw'
            out.append({
                'o': [round(ox * 10), round(oz * 10)],
                'v': [c for v in verts for c in v],
                'f': faces,
                'k': KIND[kind],
                'y': a.get('oorspronkelijkbouwjaar') or 1970,
                'fp': [c for x, z in fp for c in (round(x * 10), round(z * 10))],
                'a': addr.get(pid, []),
            })
            shapes.append(fp)
    return out, shapes
