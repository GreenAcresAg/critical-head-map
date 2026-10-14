#!/usr/bin/env python3
"""Step B1 — sample DWR InSAR cumulative displacement at every public well with >= MIN_POST readings since
mid-2015 (data/public_wells_area.csv). Same method as prep_insar_wells.py (median of 5 points <=110 m).
Output: data/insar_public.json {site_code: [[decimal_year, ft], ...]}
"""
import csv, json, os, re, statistics, urllib.parse
from prep_insar_wells import http, dec_year, SVC, DLAT, DLON

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_POST = 12


def main():
    wells = [r for r in csv.DictReader(open(f"{HERE}/data/public_wells_area.csv")) if int(r["n_since_2015"]) >= MIN_POST]
    pts, owner = [], []
    for wi, w in enumerate(wells):
        la, lo = float(w["lat"]), float(w["lon"])
        for dy, dx in ((0, 0), (DLAT, 0), (-DLAT, 0), (0, DLON), (0, -DLON)):
            pts.append([lo + dx, la + dy]); owner.append(wi)
    q = urllib.parse.urlencode({"where": "1=1", "outFields": "OBJECTID,Name", "returnGeometry": "false", "orderByFields": "OBJECTID", "f": "json"})
    rasters = [(f["attributes"]["OBJECTID"], dec_year(m.group(1))) for f in http(f"{SVC}/query?{q}")["features"]
               if (m := re.search(r"_(\d{8})$", f["attributes"]["Name"]))]
    print(f"{len(wells)} wells x 5 samples; {len(rasters)} dates")
    geom = json.dumps({"points": pts, "spatialReference": {"wkid": 4326}})
    per = [{} for _ in wells]
    for k, (oid, dy) in enumerate(rasters):
        mr = json.dumps({"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [oid]})
        res = http(f"{SVC}/getSamples", data=urllib.parse.urlencode({"geometry": geom, "geometryType": "esriGeometryMultipoint", "mosaicRule": mr, "f": "json"}))
        for s in res.get("samples", []):
            try: v = float(s["value"])
            except (ValueError, TypeError): continue
            per[owner[s["locationId"]]].setdefault(dy, []).append(v)
    out, short = {}, []
    for w, d in zip(wells, per):
        ser = [[dy, round(statistics.median(v), 4)] for dy, v in sorted(d.items())]
        (out.__setitem__(w["site_code"], ser) if len(ser) >= 20 else short.append(w["well"]))
    json.dump(out, open(f"{HERE}/data/insar_public.json", "w"))
    print(f"wrote {len(out)} series; no/short InSAR coverage: {len(short)} {short[:12]}")


if __name__ == "__main__":
    main()
