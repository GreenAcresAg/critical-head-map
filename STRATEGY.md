# Strategy — Trend-Based Critical Head, Mid-Kings River & South Fork Kings GSAs

Basis: DWR *Land Subsidence BMP* (Jan 2026) §5.3 / §5.3.1 (trend-based), with §5.3.2 (accuracy 0.067 ft, semi-annual
data acceptable) and §5.3.4 (when trend fails → empirical/modeling).

## 1. Principle
Subsidence is largely controlled by groundwater level. A **sustained period of minimal subsidence** implies levels were at or
above critical head; the level during that period approximates critical head. Prefer recent periods. Residual subsidence
means the estimate is approximate and must be re-evaluated as data accrue.

## 2. Efficient workflow
1. **Screen wells for data sufficiency** (cheap, auditable): ≥12 un-flagged readings since 2015-06-13, ≥6-yr span, no gap >2.5 yr,
   a reading in the last 3 yr. Pumping/destroyed/obstructed readings dropped. **48 wells → 20 pass** (`well_screen.csv` lists the reason for every fail:
   most failures have <12 readings in the InSAR era, i.e. the DWR export holds only sparse legacy readings).
2. **Use InSAR as the collocated displacement record** for every well (uniform, 2015→2026, every well gets one, accuracy 0.067 ft) rather than waiting on
   sparse benchmark leveling (Tulare Lake benchmarks are PDF-only annual Fall-to-Fall values).
3. **Find quiet windows**: centered 12-month displacement ≥ −0.067 ft (12 months removes the seasonal elastic cycle; centering judges each reading by the
   subsidence just before *and* after it); single-month dips bridged; window must be ≥1.5 yr.
4. **Estimate** = lowest observed groundwater elevation (ft NAVD88) inside the most recent qualifying window holding ≥2 readings.
5. **Qualify the estimate**: *Bracketed* (subsidence also observed at lower levels) vs *Upper bound only* (levels never fell low enough in the record to cause
   subsidence → critical head ≤ value); sensitivity at 0.10 ft; share of active-subsidence readings at levels *above* the estimate (residual subsidence or well/depth mismatch);
   aquifer position vs Corcoran (E) Clay; readings in window. These produce **High / Moderate / Low / Not determinable**.
6. **Route the rest**: wells with continuing subsidence and no rebound → §5.3.4: empirical analysis (same data, §5.3.2) then modeling.

## 3. Wells used
20 screened wells: Mid-Kings 11 (northern MW-A…MWH monitoring clusters, DWR wells 18S22E24D/34R, 19S22E08D002M); South Fork Kings 9 (KRCD nested KRCDAC1/3/5 sites, 18S20E34N001, 20S20E28E003M).
Wells screened in the shallow zone (<150 ft or "local") are shown as context only (Low).

## 4. Findings
**South Fork Kings — 5 bracketed estimates** (window Oct 2022 – Oct 2024, the post-2023-flood recovery; only 2–3 yr of rebound):
KRCDAC3D −46 ft and KRCDAC3M −48 ft (Moderate; both nested at one site), KRCDAC5D −11 ft (Moderate), 20S20E28E003M (below E-Clay) −42 ft (Low), KRCDAC5M +45 ft (Low – levels there do not explain subsidence; depth mismatch).
Latest (Oct 2025) levels at KRCDAC3 are ~6–8 ft **below** the estimate and at KRCDAC5D ~33 ft below → no cushion; InSAR at these sites still shows ~−0.17 ft/yr (3) .
**Not determinable (4)**: KRCDAC1D/1M/1S and 18S20E34N001M — subsidence of −5 ft since 2015 at ~−0.26 ft/yr with no sustained rebound.
**Mid-Kings — 6 upper bounds, no bracketed estimates.** North Mid-Kings (MW-A, MW-C, MWD, MWG) has barely subsided (−0.2 to −0.8 ft since 2015), so levels there never fell low enough
to reveal a threshold: MWD INT ≤174 ft, MWD DEEP ≤164 ft, MW-C ≤179 ft (Moderate), MWG INT ≤174 / DEEP ≤155 ft (Low, 2 readings), MW-A ≤213 ft (Low, shallow).
**Not determinable (5)**: the subsiding southern wells — 19S22E08D002M (below E-Clay, −5.35 ft, −0.27 ft/yr), 18S22E34R001M (−3.6 ft), MWH DEEP/INT (−3.5 ft) — no sustained rebound; 18S22E24D001M has a quiet window but <2 readings in it.

**Take-away:** the trend method yields usable numbers only where a rebound window exists (SFK 2022-24) or subsidence is negligible (north Mid-Kings). The most severe Mid-Kings subsidence
sits exactly where the method cannot bound critical head → empirical/modeling analysis is needed there (BMP §5.3.4).

## 5. Recommended next steps (cheapest first)
1. Run the **empirical method (§5.3.2)** with the same assembled data — it is the BMP's recommended refinement and reuses steps 1–2.
2. **Increase water-level frequency** at the representative wells (monthly or logger) — 3 readings per window is the main limit; add wells screened below the E-Clay near 19S22E08D002M / MWH.
3. Obtain **GSA/KRCD-held readings** not in the SGMA export (screening dropped 28 wells for sparse data).
4. Cross-check with CGPS/benchmark data and extend pre-2015 stress history (CRCN, annual Table E-1 leveling).
5. Re-evaluate each year as InSAR and levels accrue; update `data/` and rerun the three scripts.
