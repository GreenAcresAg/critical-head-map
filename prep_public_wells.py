#!/usr/bin/env python3
"""Step A2 — assemble PUBLIC groundwater-level wells around Lemoore / Hanford / Corcoran and sort them by
screened depth relative to the Corcoran (E) Clay.

Sources (all public): DWR Periodic Groundwater Level Measurements (data.cnra.ca.gov: stations, perforations,
measurements — SGMA + CASGEM + voluntary + DWR discrete), and the Corcoran Clay depths logged in DWR's 1D
subsidence-model lithology (data/dwr_1d_sites.csv, from prep_dwr_1d.py).

Usage: python3 -I prep_public_wells.py <dir with stations.csv perforations.csv measurements.csv> <dir with USGS clay shapefile folders>
Output: data/public_wells_area.csv (one row per well: location, construction, clay-relative zone, record stats)
        data/public_wells_levels.csv (usable measurements for wells with >= MIN_RECORD readings)
"""
import csv, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BOX = (35.95, 36.45, -119.95, -119.40)       # lat min/max, lon min/max : Lemoore–Hanford–Corcoran study area
MIN_RECORD = 8
LOCAL_KM = 3.0
AMBIG_FT = 60          # screen edge within this distance of a clay boundary → ambiguous zone
csv.field_size_limit(10**7)


def km(lat1, lon1, lat2, lon2):
    return 111.2 * math.hypot(lat1 - lat2, (lon1 - lon2) * math.cos(math.radians(lat1)))


def clay_model(clay_root):
    """Corcoran Clay (top, bottom) in ft below ground at a point. Local control first: a DWR 1D-model lithology site within
    LOCAL_KM uses its logged clay; elsewhere the USGS Page (1986) depth + thickness contours (validated vs 1D sites: ~+16 ft mean, 45 ft RMS)."""
    from clay_usgs import Contours
    dep = Contours(clay_root, "corcoran_clay_depth", "COR_DEPTH"); thk = Contours(clay_root, "corcoran_clay_thickness", "THICKNESS")
    pts = []
    for r in csv.DictReader(open(f"{HERE}/data/dwr_1d_sites.csv")):
        if r.get("corcoran_top_ft") and r["subbasin"] in ("Tulare Lake", "Kaweah", "Westside", "Tule", "Kings"):
            pts.append((float(r["lat"]), float(r["lon"]), float(r["corcoran_top_ft"]), float(r["corcoran_bot_ft"]), r["site"]))
    def f(lat, lon):
        d = min((km(lat, lon, p[0], p[1]), p) for p in pts)
        if d[0] <= LOCAL_KM: return d[1][2], d[1][3], d[0], "DWR 1D " + d[1][4]
        top = dep.at(lon, lat)[0]; t = thk.at(lon, lat)[0]
        return top, top + t, d[0], "USGS Page 1986"
    return f


def ambiguous(top_prf, bot_prf, ct, cb):
    if top_prf is None or bot_prf is None: return False
    return abs(top_prf - cb) <= AMBIG_FT or abs(bot_prf - ct) <= AMBIG_FT


def zone(top_prf, bot_prf, depth, ct, cb):
    if top_prf is not None and bot_prf is not None:
        if top_prf >= cb - 10: return "Lower (below Corcoran Clay)"
        if bot_prf <= ct + 10: return "Upper (above Corcoran Clay)"
        return "Composite (screens span clay)"
    if depth:
        return "Upper (depth only)" if depth <= ct else "Unknown screens, deeper than clay top"
    return "No construction data"


def main(src, clay_root):
    clay = clay_model(clay_root)
    perf = {}
    for r in csv.DictReader(open(f"{src}/perforations.csv")):
        try: perf.setdefault(r["site_code"], []).append((float(r["top_prf_int"]), float(r["bot_prf_int"])))
        except ValueError: pass
    st = {}
    for r in csv.DictReader(open(f"{src}/stations.csv")):
        try: la, lo = float(r["latitude"]), float(r["longitude"])
        except ValueError: continue
        if BOX[0] <= la <= BOX[1] and BOX[2] <= lo <= BOX[3]: st[r["site_code"]] = (r, la, lo)
    print(f"{len(st)} stations in study box")
    meas, qa = {}, {}
    with open(f"{src}/measurements.csv") as f:
        for r in csv.DictReader(f):
            s = r["site_code"]
            if s not in st: continue
            q = (r["wlm_qa_desc"] or "").strip(); qa[q] = qa.get(q, 0) + 1
            if q not in ("Good", "") or not r["gwe"]: continue          # drop pumping/questionable/no-measurement flags
            try: meas.setdefault(s, {})[r["msmt_date"][:10]] = float(r["gwe"])
            except ValueError: pass
    print("QA flags (study box):", dict(sorted(qa.items(), key=lambda x: -x[1])[:8]))
    rows, lev = [], []
    for s, (r, la, lo) in st.items():
        m = sorted(meas.get(s, {}).items())
        if not m: continue
        pf = perf.get(s)
        tp = min(p[0] for p in pf) if pf else None; bp = max(p[1] for p in pf) if pf else None
        depth = float(r["well_depth"]) if r["well_depth"] else None
        ct, cb, dkm, dsite = clay(la, lo)
        yrs = [datetime.strptime(d, "%Y-%m-%d") for d, _ in m]; ye = [y.year + y.timetuple().tm_yday / 365.25 for y in yrs]
        post = [(y, v) for y, (_, v) in zip(ye, m) if y >= 2015.45]
        gaps = [b - a for a, b in zip(ye, ye[1:])]
        lo_i = min(range(len(m)), key=lambda i: m[i][1])
        row = {"site_code": s, "stn_id": r["stn_id"], "well": r["well_name"], "swn": r["swn"], "program": r["monitoring_program"],
               "basin": r["basin_name"], "lat": la, "lon": lo, "gse_ft": r["gse"], "well_depth_ft": depth or "", "top_prf_ft": tp if tp is not None else "",
               "bot_prf_ft": bp if bp is not None else "", "wcr_no": r["wcr_no"], "use": r["well_use"],
               "clay_top_ft": round(ct), "clay_bot_ft": round(cb), "clay_ref_site": dsite, "clay_ref_km": round(dkm, 1),
               "zone": zone(tp, bp, depth, ct, cb), "zone_ambiguous": ambiguous(tp, bp, ct, cb), "n": len(m), "first": m[0][0], "last": m[-1][0], "n_since_2015": len(post),
               "max_gap_yr": round(max(gaps), 1) if gaps else "", "low_gwe_ft": m[lo_i][1], "low_date": m[lo_i][0], "latest_gwe_ft": m[-1][1]}
        rows.append(row)
        if len(m) >= MIN_RECORD:
            for d, v in m: lev.append([s, d, v])
    rows.sort(key=lambda r: (r["zone"], -r["n_since_2015"]))
    with open(f"{HERE}/data/public_wells_area.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(f"{HERE}/data/public_wells_levels.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["site_code", "date", "gwe_ft"]); w.writerows(lev)
    print(f"{len(rows)} wells with usable readings; {len(lev)} readings kept")
    import collections
    c = collections.Counter(r["zone"] for r in rows); print(dict(c))
    good = [r for r in rows if r["n_since_2015"] >= 12]
    print("wells with >=12 readings since mid-2015:", len(good), dict(collections.Counter(r["zone"] for r in good)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
