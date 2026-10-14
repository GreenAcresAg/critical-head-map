#!/usr/bin/env python3
"""Step B3 — validate DWR InSAR against public continuous GPS (NGL/EarthScope) near Lemoore / Hanford / Corcoran.
Compares vertical change 2015-06 -> end of common record at each station (InSAR = median of 5 pts <=110 m).
GPS series come from ~/insar-subsidence-map/data/cgps_*.{geojson,json}. Output: data/gps_validation.csv + data/gps_study_area.json"""
import csv, json, os, re, statistics, urllib.parse
import numpy as np
from prep_insar_wells import http, dec_year, SVC, DLAT, DLON

HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.expanduser("~/insar-subsidence-map/data")
BOX = (35.9, 36.5, -120.0, -119.35)


def main():
    st = [f for f in json.load(open(f"{SRC}/cgps_stations.geojson"))["features"]
          if BOX[0] <= f["geometry"]["coordinates"][1] <= BOX[1] and BOX[2] <= f["geometry"]["coordinates"][0] <= BOX[3]]
    ser = json.load(open(f"{SRC}/cgps_series.json"))
    pts, own = [], []
    for i, f in enumerate(st):
        lo, la = f["geometry"]["coordinates"]
        for dy, dx in ((0, 0), (DLAT, 0), (-DLAT, 0), (0, DLON), (0, -DLON)): pts.append([lo + dx, la + dy]); own.append(i)
    q = urllib.parse.urlencode({"where": "1=1", "outFields": "OBJECTID,Name", "returnGeometry": "false", "orderByFields": "OBJECTID", "f": "json"})
    rasters = [(f["attributes"]["OBJECTID"], dec_year(m.group(1))) for f in http(f"{SVC}/query?{q}")["features"] if (m := re.search(r"_(\d{8})$", f["attributes"]["Name"]))]
    per = [{} for _ in st]; geom = json.dumps({"points": pts, "spatialReference": {"wkid": 4326}})
    for oid, dy in rasters:
        mr = json.dumps({"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [oid]})
        for s in http(f"{SVC}/getSamples", data=urllib.parse.urlencode({"geometry": geom, "geometryType": "esriGeometryMultipoint", "mosaicRule": mr, "f": "json"})).get("samples", []):
            try: per[own[s["locationId"]]].setdefault(dy, []).append(float(s["value"]))
            except (ValueError, TypeError): pass
    rows, keep = [], {}
    for f, d in zip(st, per):
        sta = f["properties"]["sta"]; g = np.array(ser.get(sta, [])); ins = np.array([[k, statistics.median(v)] for k, v in sorted(d.items())])
        keep[sta] = dict(lon=f["geometry"]["coordinates"][0], lat=f["geometry"]["coordinates"][1], gps=ser.get(sta, []), insar=ins.tolist())
        if len(g) < 5 or len(ins) < 5: continue
        a = max(g[0, 0], ins[0, 0]); b = min(g[-1, 0], ins[-1, 0])
        if b - a < 1.5: continue
        gc = float(np.interp(b, g[:, 0], g[:, 1]) - np.interp(a, g[:, 0], g[:, 1])); ic = float(np.interp(b, ins[:, 0], ins[:, 1]) - np.interp(a, ins[:, 0], ins[:, 1]))
        rows.append(dict(station=sta, lat=round(f["geometry"]["coordinates"][1], 4), lon=round(f["geometry"]["coordinates"][0], 4), period=f"{a:.1f}-{b:.1f}",
                         gps_change_ft=round(gc, 2), insar_change_ft=round(ic, 2), diff_ft=round(ic - gc, 2), rate_diff_ftyr=round((ic - gc) / (b - a), 3)))
    with open(f"{HERE}/data/gps_validation.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
    json.dump(keep, open(f"{HERE}/data/gps_study_area.json", "w"))
    for r in rows: print(r)


if __name__ == "__main__":
    main()
