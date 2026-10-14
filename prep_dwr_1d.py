#!/usr/bin/env python3
"""Step A1 — extract DWR's published 1D MODFLOW-6 CSUB critical-head results (INTERA / DWR, Dec 2025;
github.com/leila-saberi/1DSubsidenceModeling-MF6CSUB, branches Multi-IB + Single-IB) for all 50 Central Valley sites.

Usage: python3 -I prep_dwr_1d.py <multi_ib_checkout> <single_ib_checkout_dir_containing_site_folders>
Output: data/dwr_1d_sites.csv  (one row per site: location, Corcoran Clay depth, calibrated mean critical head
        at 2015/2020/2024, observed lower-aquifer heads, record low), data/dwr_1d_ch_series.json (MeanCH monthly series)

MeanCH = ensemble-mean simulated critical (preconsolidation) head of the principal/lower aquifer; values after
2024 are forecast scenarios and are NOT used for the 'current' estimate. Elevations are ft above mean sea level (NAVD88).
"""
import csv, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CALIB_END = 2024.999


def dbf(p):
    f = open(p, "rb").read(); n = struct.unpack("<I", f[4:8])[0]; hl, rl = struct.unpack("<HH", f[8:12])
    fields, o = [], 32
    while f[o] != 0x0D: fields.append((f[o:o + 11].split(b"\0")[0].decode(), f[o + 16])); o += 32
    out = []
    for i in range(n):
        r = f[hl + i * rl:hl + (i + 1) * rl][1:]; d, k = {}, 0
        for nm, ln in fields: d[nm] = r[k:k + ln].decode("latin1").strip(); k += ln
        out.append(d)
    return out


def yr(s):
    m, d, y = s.split("/"); return int(y) + (int(m) - 1) / 12


def fnum(x):
    try: return float(x)
    except (ValueError, TypeError): return None


def main(multi, single):
    sites = dbf(f"{multi}/GIS/Prelim_sites_10_13_25_single_site.dbf")
    rows, series = [], {}
    for s in sites:
        key = s["Name"].replace(" ", "")
        d = next((p for p in (f"{multi}/{key}", f"{single}/{key}", f"{multi}/{s['Name']}", f"{single}/{s['Name']}") if os.path.isdir(p)), None)
        if not d and s["Name"] == "T 54 RESET 1932": d = f"{multi}/T54_RESET"
        if not d and "RESET" in s["Name"]: d = next((p for p in (f"{multi}/{key.replace('RESET','_RESET')}",) if os.path.isdir(p)), None)
        row = {"site": s["Name"], "subbasin": s["Subbasin"], "gsa": s["GSA"], "lat": fnum(s["Lat"]), "lon": fnum(s["Long"]), "status": s["Status"]}
        if not d: row["note"] = "no model folder in repo"; rows.append(row); continue
        ch = next((os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if f.endswith("MeanCH.csv")), None)
        if ch:
            rr = list(csv.reader(open(ch)))
            row["ch_layer"] = rr[0][1].replace("Mean CH - ", "").replace("Mean  CH - ", "").strip()
            ser = [(yr(a[0]), float(a[1])) for a in rr[1:] if len(a) > 1 and a[1]]
            series[s["Name"]] = [[round(a, 3), round(b, 2)] for a, b in ser if a <= CALIB_END + 0.0]
            at = lambda y: min(ser, key=lambda p: abs(p[0] - y))[1] if ser else None
            row.update(ch_2015=round(at(2015.0), 1), ch_2020=round(at(2020.0), 1), ch_2024=round(at(2024.0), 1))
        lit = next((os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if f.endswith("lithology.csv")), None)
        if lit:
            L = list(csv.DictReader(open(lit)))
            cc = [r for r in L if r["Aquifer"].lower().startswith("corcoran")]
            if cc: row["corcoran_top_ft"], row["corcoran_bot_ft"] = cc[0]["Top"], cc[-1]["Bot"]
            row["total_depth_ft"] = max(float(r["Bot"]) for r in L)
        ob = next((os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if f.endswith("obs_data.csv")), None)
        if ob:
            O = list(csv.DictReader(open(ob)))
            for aq in sorted({r["Aquifer"] for r in O}):
                v = [(yr(r["Date"]), float(r["Alt"])) for r in O if r["Aquifer"] == aq and fnum(r["Alt"]) is not None]
                if not v: continue
                lo = min(v, key=lambda p: p[1]); rec = [p for p in v if p[0] >= 2015]
                k = aq.lower()[:5]
                row[f"obs_{k}_n"] = len(v); row[f"obs_{k}_lastdate"] = round(max(p[0] for p in v), 1)
                row[f"obs_{k}_low"] = round(lo[1], 1); row[f"obs_{k}_lowyr"] = round(lo[0], 1)
                if rec: row[f"obs_{k}_med2015on"] = round(sorted(p[1] for p in rec)[len(rec) // 2], 1)
        rows.append(row)
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(f"{HERE}/data/dwr_1d_sites.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
    json.dump(series, open(f"{HERE}/data/dwr_1d_ch_series.json", "w"))
    print(f"{len(rows)} sites; {sum(1 for r in rows if 'ch_2024' in r)} with calibrated critical-head series; missing: {[r['site'] for r in rows if 'ch_2024' not in r]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
