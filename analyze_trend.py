#!/usr/bin/env python3
"""Step 3 — trend-based critical-head analysis (DWR Land Subsidence BMP, Jan 2026, §5.3.1).

Method (as the BMP describes it): subsidence is largely controlled by groundwater level; a sustained
period with minimal subsidence implies levels were at/above critical head, so the groundwater level
during that period approximates critical head. Prefer recent over historical periods. Residual
subsidence and approximate nature => report uncertainty and re-evaluate as data accrue.

Implementation, per well:
 1. InSAR cumulative displacement (step 2) → monthly grid (linear interp).
 2. Centered 12-month change  D(t) = s(t+0.5yr) − s(t−0.5yr)  (centered so each GW reading is judged by
    the subsidence both just before AND just after it; a 12-month window removes the seasonal elastic cycle).
 3. "Minimal subsidence" = D(t) >= −ACC, ACC = 0.067 ft = DWR-reported InSAR accuracy (BMP §5.3.2/Towill 2024).
 4. A "quiet window" is a run of consecutive quiet months. Footprint = run ± 0.5 yr. Sustained = ≥ MIN_FOOT yr.
 5. Pick the MOST RECENT sustained window holding ≥ 2 usable GW readings (BMP: recent > historical).
    Estimate = lowest observed groundwater elevation (GWE, ft NAVD88) among readings inside the run.
    (lowest level at which no inelastic subsidence was observed ⇒ critical head is at or below it ⇒ conservative.)
 6. Context: GWE of readings during ACTIVE subsidence (D <= −ACTIVE ft/yr) — brackets the estimate from the other
    side; counts readings with active subsidence at levels ABOVE the estimate (residual subsidence / depth
    mismatch flag).
 7. Sensitivity: repeat with ACC_RELAX = 0.10 ft; estimate stability feeds the confidence grade.
 8. Wells with no sustained quiet window are reported "not determinable by trend" → BMP §5.3.4 says use a
    modeling approach.

Outputs: data/critical_head.json (per-well series + results), data/critical_head_wells.geojson, data/critical_head_summary.csv
"""
import csv, json, os, statistics
from datetime import datetime
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D = f"{HERE}/data"
ACC, ACC_RELAX, ACTIVE = 0.067, 0.10, 0.25
MIN_FOOT = 1.5        # yr: minimum sustained quiet footprint
MIN_READINGS = 2
MONTH = 1 / 12


def dyear(s):
    d = datetime.strptime(s, "%Y-%m-%d")
    return d.year + (d.timetuple().tm_yday - 1) / 365.25


def quiet_runs(t, d, thr, bridge=2):
    """runs of consecutive grid months where d >= -thr → [(t_first, t_last)]. Dips shorter than `bridge`
    months are bridged (single-month InSAR noise should not split a multi-year quiet period)."""
    q = d >= -thr
    runs, i = [], 0
    while i < len(q):
        if q[i]:
            j = i
            while True:
                k = j + 1
                while k < len(q) and not q[k]: k += 1
                if k < len(q) and k - j - 1 <= bridge: j = k
                else: break
            runs.append((float(t[i]), float(t[j]))); i = j + 1
        else: i += 1
    return runs


def pick(runs, gw):
    """most recent run with footprint >= MIN_FOOT and >= MIN_READINGS GW readings inside"""
    for a, b in sorted(runs, key=lambda r: r[1], reverse=True):
        if (b - a) + 1.0 < MIN_FOOT: continue
        inside = [(x, v) for x, v in gw if a <= x <= b]
        if len(inside) >= MIN_READINGS:
            lo = min(inside, key=lambda r: r[1])
            return dict(start=a - 0.5, end=b + 0.5, foot_yr=round((b - a) + 1.0, 2), n=len(inside),
                        est=lo[1], est_t=lo[0], run=(a, b))
    return None


def representativeness(aq, depth, bot):
    """BMP §5.3.2: GW levels must represent the depth driving compaction. Shallow/unconfined/local wells
    sit above the compressible section, so their estimate is context only."""
    a = aq.lower()
    try: bd = float(bot or depth or 0)
    except ValueError: bd = 0
    if "local" in a or (bd and bd < 150): return "Shallow (context only)"
    if "below" in a: return "Lower aquifer (below E-Clay)"
    return "Upper aquifer (above E-Clay)"


def main():
    scr = {r["stn_id"]: r for r in csv.DictReader(open(f"{D}/well_screen.csv")) if r["pass"] == "True"}
    ins = json.load(open(f"{D}/insar_wells.json"))
    gwall = {}
    for r in csv.DictReader(open(f"{D}/gw_levels.csv")):
        gwall.setdefault(r["stn_id"], {})[r["date"]] = float(r["gwe_ft"])
    out, feats, rows = {}, [], []
    for sid, w in scr.items():
        s = np.array(ins[sid]); gw = sorted((dyear(k), v) for k, v in gwall[sid].items())
        t = np.arange(s[0, 0] + 0.5, s[-1, 0] - 0.5 + 1e-9, MONTH)
        f = lambda x: np.interp(x, s[:, 0], s[:, 1])
        dt = f(t + 0.5) - f(t - 0.5)                       # centered 12-mo change (ft)
        D_at = lambda x: float(np.interp(x, t, dt)) if t[0] <= x <= t[-1] else None
        era = [(x, v) for x, v in gw if x >= s[0, 0] + 0.5 and x <= s[-1, 0] - 0.5]   # readings with a defined D
        res = pick(quiet_runs(t, dt, ACC), era)
        rel = pick(quiet_runs(t, dt, ACC_RELAX), era)
        active = [(x, v) for x, v in era if D_at(x) is not None and D_at(x) <= -ACTIVE]
        rec = dict(stn_id=sid, well=w["well"], gsa=w["gsa"], aquifer=w["aquifer"], lat=float(w["lat"]), lon=float(w["lon"]),
                   well_depth_ft=w["well_depth_ft"], top_perf_ft=w["top_perf_ft"], bot_perf_ft=w["bot_perf_ft"],
                   gse_ft=float(w["gse_ft"]) if w["gse_ft"] else None, grade=w["grade"], n_total=int(w["n_total"]),
                   n_era=int(w["n_insar_era"]), gw_first=w["first"], gw_last=w["last"],
                   insar_total_ft=round(float(s[-1, 1]), 2), insar_end=round(float(s[-1, 0]), 2),
                   insar_rate_ftyr=round(float(np.polyfit(s[:, 0], s[:, 1], 1)[0]), 3),
                   recent_rate_ftyr=round(float(f(s[-1, 0]) - f(max(s[0, 0], s[-1, 0] - 2.0))) / min(2.0, s[-1, 0] - s[0, 0]), 3),
                   hist_low_ft=round(min(v for _, v in gw), 2), era_low_ft=round(min(v for _, v in era), 2) if era else None,
                   latest_ft=round(gw[-1][1], 2), latest_date=w["last"])
        quiet_all = [(a - 0.5, b + 0.5) for a, b in quiet_runs(t, dt, ACC) if (b - a) + 1 >= MIN_FOOT]
        rep = representativeness(w["aquifer"], w["well_depth_ft"], w["bot_perf_ft"])
        rec["representativeness"] = rep
        used, thr_used = (res, ACC) if res else (rel, ACC_RELAX)
        if used:
            est = used["est"]; other = rel if used is res else None
            est_r = other["est"] if other else (est if used is rel else None)
            above = [v for x, v in active if v > est]
            below = [v for _, v in active if v <= est]
            frac_above = len(above) / len(active) if active else 0
            stable = est_r is not None and abs(est_r - est) <= 10
            conf = ("High" if used["foot_yr"] >= 2.0 and used["n"] >= 4 and stable else
                    "Moderate" if used["foot_yr"] >= 1.5 and used["n"] >= 3 else "Low")
            notes = []
            if used is rel: conf = "Low"; notes.append("quiet window only at relaxed 0.10 ft threshold")
            if frac_above > 0.4:
                conf = {"High": "Moderate", "Moderate": "Low"}.get(conf, "Low")
                notes.append(f"subsidence also occurred at {len(above)} of {len(active)} higher readings (residual subsidence or depth mismatch)")
            if rep.startswith("Shallow"): conf = "Low"; notes.append("shallow well — not representative of compaction depth")
            if used["n"] < 4: notes.append(f"only {used['n']} readings in window — seasonal low may be missed")
            basis = "Bracketed" if below else "Upper bound only"
            if not below and conf == "High": conf = "Moderate"      # a bound is not a threshold estimate
            if not below: notes.append("levels never fell low enough to cause subsidence in record: critical head is at or below this level")
            rec.update(est_ft=round(est, 1), est_date=round(used["est_t"], 2), win_start=round(used["start"], 2),
                       win_end=round(used["end"], 2), win_yr=used["foot_yr"], win_n=used["n"], confidence=conf, basis=basis,
                       thr_ft=thr_used, sens_est_ft=round(est_r, 1) if est_r is not None else None, sens_stable=bool(stable),
                       active_n=len(active), active_median_ft=round(statistics.median(v for _, v in active), 1) if active else None,
                       active_above_est=len(above), notes="; ".join(notes),
                       cushion_ft=round(gw[-1][1] - est, 1),
                       est_dtw_ft=round(rec["gse_ft"] - est, 1) if rec["gse_ft"] else None,
                       status="Above estimate" if gw[-1][1] >= est else "Below estimate",
                       recent=bool(used["end"] >= s[-1, 0] - 3))
        else:
            long_q = [r for r in quiet_runs(t, dt, ACC_RELAX) if (r[1] - r[0]) + 1.0 >= MIN_FOOT]
            if long_q:
                why = "Sustained quiet window exists but <2 groundwater readings fall inside it — need more frequent water-level data"
            else:
                why = "Subsidence continuing with no sustained rebound — trend method cannot bound critical head; use empirical/modeling analysis (BMP §5.3.4)"
            rec.update(est_ft=None, confidence="Not determinable", basis=why, notes=why, status="n/a", active_n=len(active))
        rec["quiet_windows"] = [[round(a, 2), round(b, 2)] for a, b in quiet_all]
        rec["insar"] = [[round(float(a), 3), round(float(b), 3)] for a, b in s]
        rec["rate"] = [[round(float(a), 3), round(float(b), 3)] for a, b in zip(t, dt)]
        rec["gw"] = [[round(x, 3), v] for x, v in gw]
        out[sid] = rec
        keep = {k: v for k, v in rec.items() if k not in ("insar", "rate", "gw", "quiet_windows")}
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [rec["lon"], rec["lat"]]}, "properties": keep})
        rows.append(keep)
    json.dump(out, open(f"{D}/critical_head.json", "w"))
    json.dump({"type": "FeatureCollection", "features": feats}, open(f"{D}/critical_head_wells.geojson", "w"))
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(f"{D}/critical_head_summary.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, cols); wr.writeheader(); wr.writerows(sorted(rows, key=lambda r: (r["gsa"], r["well"])))
    for r in sorted(rows, key=lambda r: (r["gsa"], r["well"])):
        print(f"{r['gsa'][:5]} {r['well']:15} {r['aquifer'][:12]:12} insar={r['insar_total_ft']:+.2f} "
              f"est={r.get('est_ft')} win={r.get('win_start')}-{r.get('win_end')} n={r.get('win_n')} conf={r['confidence']} "
              f"{(r.get('basis') or '')[:20]} sens={r.get('sens_est_ft')} act_above={r.get('active_above_est')}/{r.get('active_n')} {r['representativeness'][:5]} "
              f"latest={r['latest_ft']} low={r['hist_low_ft']}")


if __name__ == "__main__":
    main()
