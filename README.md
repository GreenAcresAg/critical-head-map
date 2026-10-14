# Critical Head Map — Mid-Kings River & South Fork Kings GSAs (Tulare Lake subbasin)

Trend-based critical-head estimates at representative SGMA monitoring wells, following the
**DWR Land Subsidence BMP (Jan 2026), §5.3.1 "Trend-based Analysis"**, visualised as an interactive
MapLibre map in the same shell as the InSAR Land Subsidence map. Built by Green Acres Consulting, Inc.

`cd ~/critical-head-map && python3 server.py 8002` → http://localhost:8002 (deep link: `#well=KRCDAC3D`)

## Strategy (efficient, ~3 scripts, minutes to re-run)
Full write-up: **[STRATEGY.md](STRATEGY.md)**.

| Step | Script | What |
|---|---|---|
| 1 Screen | `prep_wells.py` | 48 SGMA wells in the two GSAs → 20 with enough un-flagged readings overlapping the InSAR era (auditable pass/fail reasons in `data/well_screen.csv`) |
| 2 Collocate | `prep_insar_wells.py` | DWR TRE ALTAMIRA cumulative displacement (130 monthly rasters, Jun 2015→Apr 2026) sampled at each well (median of 5 points ≤110 m) — 130 REST calls total |
| 3 Analyse | `analyze_trend.py` | Quiet-window detection → critical-head estimate, bracket, confidence grade, sensitivity → `data/critical_head*.{json,geojson,csv}` |
| 4 Visualise | `index.html`, `app.js` | Map + per-well two-panel chart (groundwater elevation / InSAR on a shared time axis) |

Rerun after new data: refresh `~/sgma-annual-report-data`, then `python3 prep_wells.py && python3 prep_insar_wells.py && python3 analyze_trend.py`.

## Results (as of data through 2025-10; InSAR through 2026-04)
See `data/critical_head_summary.csv`, STRATEGY.md §4 for interpretation.

## Caveats
- Trend-based = approximate by design (BMP §5.3.1); estimates are the **lowest observed level in a sustained minimal-subsidence window**, i.e. the true critical head is at or below it (conservative), but the seasonal low may be missed with semi-annual readings.
- InSAR cells are 100 m; wells are collocated, not co-measured. Residual subsidence and depth mismatch are flagged per well.
- GW data are the DWR SGMA-portal export (Mid-Kings through Mar 2025, South Fork Kings through Oct 2025); GSA-held data (e.g. KRCD continuous or more frequent readings) would sharpen results.
