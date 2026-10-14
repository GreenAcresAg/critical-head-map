#!/usr/bin/env python3
"""Step 1 — screen SGMA monitoring wells in Mid-Kings River + South Fork Kings GSAs (Tulare Lake
subbasin) for the trend-based critical-head analysis (DWR Land Subsidence BMP, Jan 2026, §5.3.1).

Why screen: a trend-based estimate needs a groundwater-level record that OVERLAPS the DWR InSAR
record (2015-06-13 → present) and is dense enough to resolve seasonal highs/lows. So we keep only wells with
  - usable (un-flagged) water-level measurements, GWE in ft NAVD88
  - >= MIN_N measurements inside the InSAR era, spanning >= MIN_SPAN_YR years, no gap > MAX_GAP_YR
    (the DWR export is mostly semi-annual spring/fall readings, which the BMP accepts for seasonal highs/lows)
  - a measurement within RECENT_YR years of the newest data in the export
Every well gets its metrics + a pass/fail reason so the screening is auditable.

Inputs : ../sgma-annual-report-data/data/{groundwater_level_sites,groundwater_level_data}.csv
Outputs: data/gw_levels.csv (clean measurements, target GSAs), data/well_screen.csv
"""
import csv, os, statistics
from datetime import datetime

SRC = os.path.expanduser("~/sgma-annual-report-data/data")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
GSAS = ("Mid-Kings River GSA", "South Fork Kings GSA")
INSAR_START = datetime(2015, 6, 13)
MIN_N, MIN_SPAN_YR, RECENT_YR, MAX_GAP_YR = 12, 6.0, 3.0, 2.5   # semi-annual (spring/fall) data is acceptable per BMP §5.3.2


def yr(d): return d.year + (d.timetuple().tm_yday - 1) / 365.25


def main():
    sites = {r["STN_ID"]: r for r in csv.DictReader(open(f"{SRC}/groundwater_level_sites.csv"))
             if r["AGENCY"] in GSAS and "Tulare Lake" in r["BASIN_NAME"]}
    meas, dropped = {}, 0
    for r in csv.DictReader(open(f"{SRC}/groundwater_level_data.csv")):
        if r["STN_ID"] not in sites: continue
        if r["WLM_QA_DESC"].strip() or not r["GWE"].strip():   # pumping / destroyed / obstructed / blank
            dropped += 1; continue
        d = datetime.strptime(r["MSMT_DATE"][:10], "%Y-%m-%d")
        meas.setdefault(r["STN_ID"], {})[d] = float(r["GWE"])   # de-dupe same-day
    latest = max(d for m in meas.values() for d in m)
    print(f"{len(sites)} candidate wells, {sum(len(m) for m in meas.values())} usable measurements "
          f"({dropped} QA-flagged/blank dropped); newest measurement {latest.date()}")

    rows, clean = [], []
    for sid, s in sites.items():
        m = sorted(meas.get(sid, {}).items())
        era = [(d, v) for d, v in m if d >= INSAR_START]
        row = {"stn_id": sid, "well": s["WELL_NAME"], "gsa": s["AGENCY"], "aquifer": s["PRINCIPAL_AQUIFER"],
               "lat": s["LATITUDE"], "lon": s["LONGITUDE"], "well_depth_ft": s["WELL_DEPTH"],
               "top_perf_ft": s["TOP_PRF"], "bot_perf_ft": s["BOT_PRF"], "gse_ft": s["LAST_GSE"],
               "network": s["MONITORING_NETWORK_TYPE"], "n_total": len(m),
               "first": m[0][0].date() if m else "", "last": m[-1][0].date() if m else "",
               "n_insar_era": len(era)}
        reason = []
        if len(era) < MIN_N: reason.append(f"only {len(era)} readings since 2015-06 (<{MIN_N})")
        else:
            span = yr(era[-1][0]) - yr(era[0][0])
            row["era_span_yr"] = round(span, 1)
            row["median_gap_days"] = statistics.median((b[0] - a[0]).days for a, b in zip(era, era[1:]))
            if span < MIN_SPAN_YR: reason.append(f"InSAR-era span {span:.1f} yr (<{MIN_SPAN_YR})")
            row["max_gap_yr"] = round(max((b[0] - a[0]).days for a, b in zip(era, era[1:])) / 365.25, 1)
            row["grade"] = "A" if len(era) >= 18 and row["median_gap_days"] <= 200 else "B"
            if row["max_gap_yr"] > MAX_GAP_YR: reason.append(f"gap of {row['max_gap_yr']} yr in InSAR era")
            if (latest - era[-1][0]).days / 365.25 > RECENT_YR: reason.append("no recent readings")
        row["pass"] = not reason
        row["reason"] = "; ".join(reason) or "ok"
        rows.append(row)
        if row["pass"] or m:
            for d, v in m: clean.append([sid, s["WELL_NAME"], d.date().isoformat(), v])
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(f"{OUT}/well_screen.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(sorted(rows, key=lambda r: (not r["pass"], r["gsa"], r["well"])))
    with open(f"{OUT}/gw_levels.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["stn_id", "well", "date", "gwe_ft"]); w.writerows(clean)
    ok = [r for r in rows if r["pass"]]
    print(f"{len(ok)} of {len(rows)} wells pass screening")
    for r in sorted(ok, key=lambda r: (r["gsa"], r["well"])):
        print(f"  {r['gsa'][:9]:9} {r['well']:18} {r['aquifer'][:14]:14} n_era={r['n_insar_era']:3} span={r['era_span_yr']:4} gap={r['median_gap_days']:5.0f}d max={r['max_gap_yr']}y {r['grade']}  {r['first']} → {r['last']}")


if __name__ == "__main__":
    main()
