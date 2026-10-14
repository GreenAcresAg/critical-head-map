"""USGS Page (1986) Corcoran Clay depth + thickness contours (CVHM; ScienceBase 63140570d34e36012efa2bf9) → interpolation.
Contours are NAD83 Albers (parameters read from the .prj). Interpolation between the two nearest distinct contour levels
(inverse-distance between the nearest contour of each level) — the standard hand-contouring rule."""
import math, re, struct, os


def read_prj(p):
    t = open(p).read()
    g = lambda k: float(re.search(rf'PARAMETER\["{k}",([-\d.]+)\]', t).group(1))
    return dict(lat1=g("Standard_Parallel_1"), lat2=g("Standard_Parallel_2"), lat0=g("Latitude_Of_Origin"), lon0=g("Central_Meridian"),
                fe=g("False_Easting"), fn=g("False_Northing"))


def albers(lon, lat, P):
    a, f = 6378137.0, 1 / 298.257222101; e2 = f * (2 - f); e = math.sqrt(e2)
    def q(phi):
        s = math.sin(phi); return (1 - e2) * (s / (1 - e2 * s * s) - 1 / (2 * e) * math.log((1 - e * s) / (1 + e * s)))
    def m(phi): s = math.sin(phi); return math.cos(phi) / math.sqrt(1 - e2 * s * s)
    r = math.radians
    p1, p2, p0 = r(P["lat1"]), r(P["lat2"]), r(P["lat0"])
    n = (m(p1) ** 2 - m(p2) ** 2) / (q(p2) - q(p1)); C = m(p1) ** 2 + n * q(p1)
    rho0 = a * math.sqrt(C - n * q(p0)) / n; rho = a * math.sqrt(C - n * q(r(lat))) / n; th = n * (r(lon) - r(P["lon0"]))
    return P["fe"] + rho * math.sin(th), P["fn"] + rho0 - rho * math.cos(th)


def read_lines(shp, dbf_field, dbf):
    f = open(shp, "rb").read(); o = 100; geoms = []
    while o < len(f):
        ln = struct.unpack(">i", f[o + 4:o + 8])[0] * 2; rec = f[o + 8:o + 8 + ln]; o += 8 + ln
        t = struct.unpack("<i", rec[:4])[0]
        if t not in (3, 13, 23): geoms.append([]); continue
        np_, npt = struct.unpack("<ii", rec[36:44]); parts = list(struct.unpack(f"<{np_}i", rec[44:44 + 4 * np_])) + [npt]
        pts = struct.unpack(f"<{2 * npt}d", rec[44 + 4 * np_:44 + 4 * np_ + 16 * npt]); pts = list(zip(pts[0::2], pts[1::2]))
        geoms.append([pts[parts[i]:parts[i + 1]] for i in range(np_)])
    d = open(dbf, "rb").read(); n = struct.unpack("<I", d[4:8])[0]; hl, rl = struct.unpack("<HH", d[8:12]); fields, k = [], 32
    while d[k] != 0x0D: fields.append((d[k:k + 11].split(b"\0")[0].decode(), d[k + 16])); k += 32
    vals = []
    for i in range(n):
        r = d[hl + i * rl:hl + (i + 1) * rl][1:]; c = 0
        for nm, ln in fields:
            if nm == dbf_field: vals.append(float(r[c:c + ln])); break
            c += ln
    return list(zip(vals, geoms))


def seg_dist(px, py, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - a[0]) * dx + (py - a[1]) * dy) / L))
    return math.hypot(px - a[0] - t * dx, py - a[1] - t * dy)


class Contours:
    def __init__(self, root, name, field):
        self.P = read_prj(f"{root}/{name}/{name}_feet.prj" if os.path.exists(f"{root}/{name}/{name}_feet.prj") else f"{root}/{name}/{name}.prj")
        self.lines = read_lines(f"{root}/{name}/{name}_feet.shp", field, f"{root}/{name}/{name}_feet.dbf")
        self.levels = sorted({v for v, _ in self.lines})

    def at(self, lon, lat):
        x, y = albers(lon, lat, self.P); best = {}
        for v, parts in self.lines:
            for pts in parts:
                # cheap bbox reject
                for a, b in zip(pts, pts[1:]):
                    if abs(a[0] - x) > 6e4 and abs(b[0] - x) > 6e4 and (a[0] - x) * (b[0] - x) > 0: continue
                    d = seg_dist(x, y, a, b)
                    if d < best.get(v, 1e18): best[v] = d
        near = sorted((d, v) for v, d in best.items())[:2]
        (d1, v1), (d2, v2) = near
        val = v1 if d1 + d2 == 0 else (v1 * d2 + v2 * d1) / (d1 + d2)
        return val, d1 / 1000, v1, v2
