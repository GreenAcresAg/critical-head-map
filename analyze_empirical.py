#!/usr/bin/env python3
"""Step B2 — EMPIRICAL critical-head analysis (DWR Land Subsidence BMP Jan 2026, §5.3.2) on public wells.

BMP procedure implemented:
  (a) maximum subsidence to date = running minimum of InSAR cumulative displacement (the 'red line')
  (b) 'sufficient rebound' = displacement above that line by >= ACC (0.067 ft, DWR InSAR accuracy) — elastic recovery
  (c) for each contiguous rebound period take the LOWEST groundwater level (observed readings + linear interpolation
      between readings no more than MAX_INTERP_YR apart); that series of lows is the critical-head estimate
Additions (documented judgment calls): InSAR is smoothed with a 3-month running median (single-month noise);
a rebound period must last >= 2 months; one-month dips are bridged. Estimates are graded on the number of independent rebound
periods, their agreement, and the density of water-level data inside them, and compared with the nearest DWR 1D-model critical head.
Outputs: data/empirical_wells.json (series + results), data/empirical_summary.csv
"""
import csv, json, math, os
from datetime import datetime
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); D = f"{HERE}/data"
ACC, ACC2 = 0.067, 0.10
MAX_INTERP_YR = 1.0
MIN_MONTHS = 2


def dyear(s):
    d = datetime.strptime(s, "%Y-%m-%d"); return d.year + (d.timetuple().tm_yday - 1) / 365.25


def km(a, b, c, d): return 111.2 * math.hypot(a - c, (b - d) * math.cos(math.radians(a)))


def periods(flag, t, bridge=1):
    runs, i = [], 0
    while i < len(flag):
        if flag[i]:
            j = i
            while True:
                k = j + 1
                while k < len(flag) and not flag[k]: k += 1
                if k < len(flag) and k - j - 1 <= bridge: j = k
                else: break
            if j - i + 1 >= MIN_MONTHS: runs.append((i, j))
            i = j + 1
        else: i += 1
    return runs


def analyse(t, v, gw, thr):
    vs = np.array([np.median(v[max(0, i - 1):i + 2]) for i in range(len(v))])
    runmin = np.minimum.accumulate(vs)
    flag = (vs - runmin) >= thr
    gx = np.array([a for a, _ in gw]); gy = np.array([b for _, b in gw])
    out = []
    for i, j in periods(flag, t):
        a, b = t[i], t[j]
        obs = [(x, y) for x, y in gw if a <= x <= b]
        # interpolated monthly levels inside the period, only where bracketing readings are close enough
        lv = []
        for tm in t[i:j + 1]:
            k = np.searchsorted(gx, tm)
            if 0 < k < len(gx) and gx[k] - gx[k - 1] <= MAX_INTERP_YR: lv.append(float(np.interp(tm, gx, gy)))
        cand = [y for _, y in obs] + lv
        if not cand: continue
        out.append(dict(start=round(float(a), 2), end=round(float(b), 2), months=int(j - i + 1), n_obs=len(obs),
                        low=round(min(cand), 1), rebound_ft=round(float((vs[i:j + 1] - runmin[i:j + 1]).max()), 3)))
    return out, [[round(float(x), 3), round(float(y), 3)] for x, y in zip(t, runmin)]


def main():
    W = {r["site_code"]: r for r in csv.DictReader(open(f"{D}/public_wells_area.csv"))}
    ins = json.load(open(f"{D}/insar_public.json"))
    lev = {}
    for r in csv.DictReader(open(f"{D}/public_wells_levels.csv")): lev.setdefault(r["site_code"], {})[r["date"]] = float(r["gwe_ft"])
    S1 = [r for r in csv.DictReader(open(f"{D}/dwr_1d_sites.csv")) if r.get("ch_2024") and r["subbasin"] in ("Tulare Lake", "Kaweah", "Westside", "Tule", "Kings")]
    res, rows = {}, []
    for sc, series in ins.items():
        w = W[sc]; s = np.array(series); t = np.arange(s[0, 0], s[-1, 0], 1 / 12); v = np.interp(t, s[:, 0], s[:, 1])
        gw = sorted((dyear(d), y) for d, y in lev[sc].items())
        per, runmin = analyse(t, v, gw, ACC); per2, _ = analyse(t, v, gw, ACC2)
        la, lo = float(w["lat"]), float(w["lon"])
        near = min(S1, key=lambda r: km(la, lo, float(r["lat"]), float(r["lon"]))); nkm = km(la, lo, float(near["lat"]), float(near["lon"]))
        rec = dict(site_code=sc, well=w["well"], program=w["program"], basin=w["basin"], lat=la, lon=lo, zone=w["zone"],
                   top_prf_ft=w["top_prf_ft"], bot_prf_ft=w["bot_prf_ft"], well_depth_ft=w["well_depth_ft"], gse_ft=w["gse_ft"],
                   clay_top_ft=w["clay_top_ft"], clay_bot_ft=w["clay_bot_ft"], clay_ref_km=w["clay_ref_km"], clay_ref_site=w["clay_ref_site"], zone_ambiguous=(w["zone_ambiguous"] == "True"), n=int(w["n"]),
                   first=w["first"][:10], last=w["last"][:10], n_since_2015=int(w["n_since_2015"]),
                   record_low_ft=float(w["low_gwe_ft"]), latest_ft=float(w["latest_gwe_ft"]),
                   insar_total_ft=round(float(s[-1, 1]), 2), insar_end=round(float(s[-1, 0]), 2),
                   recent_rate_ftyr=round(float(np.interp(s[-1, 0], s[:, 0], s[:, 1]) - np.interp(s[-1, 0] - 2, s[:, 0], s[:, 1])) / 2, 3),
                   dwr1d_site=near["site"], dwr1d_km=round(nkm, 1), dwr1d_ch_2024=float(near["ch_2024"]), dwr1d_layer=near.get("ch_layer", ""))
        wmed = float(np.median([y for x, y in gw if x >= 2015.45]))
        m1d = near.get("obs_lower_med2015on")
        rec["well_median_2015on"] = round(wmed, 1); rec["dwr1d_obs_median_2015on"] = float(m1d) if m1d else None
        # only compare with a 1D site if it is close AND in the same head regime (median level since 2015 within 40 ft)
        rec["comparable_1d"] = bool(m1d and nkm <= 15 and abs(wmed - float(m1d)) <= 40 and ("Lower" in w["zone"] or "Composite" in w["zone"]))
        good = [p for p in per if p["months"] >= 2]
        rec["n_periods"] = len(good); rec["rebound_months"] = sum(p["months"] for p in good)
        if good:
            lows = [p["low"] for p in good]; last = max(good, key=lambda p: p["end"])
            spread = max(lows) - min(lows)
            dense = sum(p["n_obs"] for p in good)
            conf = ("High" if len(good) >= 2 and spread <= 15 and dense >= 12 else
                    "Moderate" if (len(good) >= 2 and spread <= 30) or (sum(p["months"] for p in good) >= 6 and dense >= 3) else "Low")
            rec.update(emp_ch_latest=last["low"], emp_ch_min=min(lows), emp_ch_max=max(lows), emp_spread_ft=round(spread, 1),
                       emp_obs_in_periods=dense, emp_conf=conf, emp_ch_thr10=(max(per2, key=lambda p: p["end"])["low"] if per2 else None),
                       emp_last_period=f"{last['start']:.2f}-{last['end']:.2f}",
                       diff_vs_1d=round(last["low"] - rec["dwr1d_ch_2024"], 1) if rec["comparable_1d"] else None)
        else:
            rec.update(emp_conf="Not determinable", emp_ch_latest=None)
        res[sc] = dict(rec, periods=good, runmin=runmin[::2], insar=[[round(a, 3), round(b, 3)] for a, b in series],
                       gw=[[round(x, 3), y] for x, y in gw if x > 1990])
        rows.append(rec)
    json.dump(res, open(f"{D}/empirical_wells.json", "w"))
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]}, "properties": r} for r in rows]
    json.dump({"type": "FeatureCollection", "features": feats}, open(f"{D}/public_wells.geojson", "w"))
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(f"{D}/empirical_summary.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, cols); wr.writeheader(); wr.writerows(sorted(rows, key=lambda r: (r["zone"], r["well"])))
    import collections
    print(len(rows), "wells;", dict(collections.Counter(r["emp_conf"] for r in rows)))
    for z in ("Lower", "Composite", "Upper", "No constr", "Unknown"):
        g = [r for r in rows if r["zone"].startswith(z)]
        print(f"  {z:10} n={len(g):3} determinable={sum(1 for r in g if r['emp_ch_latest'] is not None)}")
    print(f"{'well':16}{'zone':6}{'insar':>6}{'per':>4}{'mo':>4}{'emp CH':>8}{'rng':>14}{'conf':>10}{'1D CH':>7}{'km':>5}{'cmp':>5}{'diff':>6}")
    for r in sorted(rows, key=lambda r: (r["zone"], r["well"])):
        if r["zone"].startswith(("Lower", "Composite")):
            print(f"{r['well'][:15]:16}{r['zone'][:5]:6}{r['insar_total_ft']:6.1f}{r['n_periods']:4}{r['rebound_months']:4}{str(r['emp_ch_latest']):>8}"
                  f"{(str(r.get('emp_ch_min'))+'..'+str(r.get('emp_ch_max'))) if r['emp_ch_latest'] is not None else '':>14}{r['emp_conf'][:9]:>10}{r['dwr1d_ch_2024']:7.0f}{r['dwr1d_km']:5.0f}{str(r.get('diff_vs_1d')):>6}")


if __name__ == "__main__":
    main()
