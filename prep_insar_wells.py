#!/usr/bin/env python3
"""Step 2 — sample DWR TRE ALTAMIRA InSAR cumulative vertical displacement at every screened well.

Same endpoint/pattern as ~/insar-subsidence-map/prep_insar_benchmarks.py: one getSamples multipoint call
per dated raster (~132 monthly rasters, 2015-06 → present), values in FEET, negative = subsidence.

Each well is sampled at its coordinate plus 4 neighbours ~110 m away (N/S/E/W); the reported series is
the per-date MEDIAN of the valid samples. InSAR cells are 100 m averages and a single cell can be NoData
or noisy, so the median of 5 is more robust than the single centre cell and still "collocated".

Output: data/insar_wells.json  {stn_id: [[decimal_year, cum_disp_ft], ...]}
"""
import csv, json, os, re, statistics, time, urllib.parse, urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SVC = ("https://gis.water.ca.gov/arcgisimg/rest/services/SAR/"
       "Vertical_Displacement_TRE_ALTAMIRA_Total_Since_20150613_Mosaic/ImageServer")
DLAT, DLON = 0.001, 0.0012     # ~110 m


def http(url, data=None, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data.encode() if data else None), timeout=90) as r:
                return json.load(r)
        except Exception:
            if i == tries - 1: raise
            time.sleep(2 * (i + 1))


def dec_year(s):
    d = datetime.strptime(s, "%Y%m%d")
    return round(d.year + (d - datetime(d.year, 1, 1)).days / 365.25, 4)


def main():
    wells = [r for r in csv.DictReader(open(f"{HERE}/data/well_screen.csv")) if r["pass"] == "True"]
    pts, owner = [], []
    for wi, w in enumerate(wells):
        lat, lon = float(w["lat"]), float(w["lon"])
        for dy, dx in ((0, 0), (DLAT, 0), (-DLAT, 0), (0, DLON), (0, -DLON)):
            pts.append([lon + dx, lat + dy]); owner.append(wi)
    q = urllib.parse.urlencode({"where": "1=1", "outFields": "OBJECTID,Name", "returnGeometry": "false",
                                "orderByFields": "OBJECTID", "f": "json"})
    rasters = [(f["attributes"]["OBJECTID"], dec_year(m.group(1))) for f in http(f"{SVC}/query?{q}")["features"]
               if (m := re.search(r"_(\d{8})$", f["attributes"]["Name"]))]
    print(f"{len(wells)} wells × 5 samples; {len(rasters)} InSAR dates")
    geom = json.dumps({"points": pts, "spatialReference": {"wkid": 4326}})
    per = [{} for _ in wells]
    for k, (oid, dy) in enumerate(rasters):
        mr = json.dumps({"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [oid]})
        res = http(f"{SVC}/getSamples", data=urllib.parse.urlencode(
            {"geometry": geom, "geometryType": "esriGeometryMultipoint", "mosaicRule": mr, "f": "json"}))
        for s in res.get("samples", []):
            try: v = float(s["value"])
            except (ValueError, TypeError): continue
            per[owner[s["locationId"]]].setdefault(dy, []).append(v)
        if (k + 1) % 20 == 0: print(f"  {k + 1}/{len(rasters)}")
    out, empty = {}, []
    for w, d in zip(wells, per):
        ser = [[dy, round(statistics.median(v), 4)] for dy, v in sorted(d.items())]
        (out.__setitem__(w["stn_id"], ser) if len(ser) >= 20 else empty.append(w["well"]))
    json.dump(out, open(f"{HERE}/data/insar_wells.json", "w"))
    print(f"wrote {len(out)} series; no/short InSAR coverage: {empty or 'none'}")
    for w in wells:
        s = out.get(w["stn_id"])
        if s: print(f"  {w['well']:16} n={len(s)} total {s[-1][1]:+.2f} ft ({s[0][0]:.1f}→{s[-1][0]:.1f})")


if __name__ == "__main__":
    main()
