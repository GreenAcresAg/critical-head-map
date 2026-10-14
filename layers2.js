/* ══════════════════════════════════════════════════════════════════
   Public-data layers (Lemoore · Hanford · Corcoran): DWR 1D-model critical head sites, public wells sorted by depth vs the
   Corcoran Clay with EMPIRICAL critical-head results (BMP §5.3.2), and public GPS stations validating InSAR.
   Shares globals (map, esc, fmt, fdate, getJSON) with app.js.
   ══════════════════════════════════════════════════════════════════ */
const ZONE = { "Lower": "#38bdf8", "Composite": "#a78bfa", "Upper": "#fbbf24", "No constr": "#94a3b8", "Unknown": "#94a3b8" };
const zkey = z => /^Lower/.test(z) ? "Lower" : /^Composite/.test(z) ? "Composite" : /^Upper/.test(z) ? "Upper" : "No constr";
const C_1D = "#c084fc", C_RUN = "#94a3b8", C_REB = "#34d399", C_EMP = "#f87171";
let pubFull = null, dwrSeries = null, gpsData = null, dwrProps = {};

map.on("load", async () => {
    const [pubGeo, dwrGeo, gps] = await Promise.all([getJSON("data/public_wells.geojson"), getJSON("data/dwr_1d_sites.geojson"), getJSON("data/gps_study_area.json")]);
    gpsData = gps; dwrGeo.features.forEach(f => dwrProps[f.properties.site] = f.properties);
    pubGeo.features.forEach(f => { f.properties.zk = zkey(f.properties.zone); f.properties.det = f.properties.emp_ch_latest != null ? 1 : 0; });
    map.addSource("pub", { type: "geojson", data: pubGeo });
    map.addLayer({ id: "pub-wells", type: "circle", source: "pub", paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, ["case", ["==", ["get", "det"], 1], 4.5, 3], 14, ["case", ["==", ["get", "det"], 1], 10, 6]],
        "circle-color": ["match", ["get", "zk"], "Lower", ZONE.Lower, "Composite", ZONE.Composite, "Upper", ZONE.Upper, ZONE["No constr"]],
        "circle-opacity": ["case", ["boolean", ["get", "zone_ambiguous"], false], 0.55, 0.95],
        "circle-stroke-color": ["case", ["==", ["get", "det"], 1], "#ffffff", "#0f172a"], "circle-stroke-width": ["case", ["==", ["get", "det"], 1], 2.2, 0.8] } });
    map.addLayer({ id: "pub-label", type: "symbol", source: "pub", minzoom: 11.5, filter: ["==", ["get", "det"], 1], layout: {
        "text-field": ["concat", ["get", "well"], "\n", ["to-string", ["get", "emp_ch_latest"]], " ft"], "text-size": 10, "text-font": ["Noto Sans Bold"], "text-offset": [0, 1.5], "text-anchor": "top" },
        paint: { "text-color": "#e0f2fe", "text-halo-color": "#0f172a", "text-halo-width": 1.6 } });
    map.addSource("dwr1d", { type: "geojson", data: dwrGeo });
    map.addLayer({ id: "dwr1d", type: "circle", source: "dwr1d", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 6, 14, 12], "circle-color": C_1D, "circle-stroke-color": "#fff", "circle-stroke-width": 2 } });
    map.addLayer({ id: "dwr1d-label", type: "symbol", source: "dwr1d", minzoom: 9.5, layout: {
        "text-field": ["concat", "1D model ", ["get", "site"], "\nCH ", ["to-string", ["get", "ch_2024"]], " ft"], "text-size": 10.5, "text-font": ["Noto Sans Bold"], "text-offset": [0, 1.6], "text-anchor": "top" },
        paint: { "text-color": "#f3e8ff", "text-halo-color": "#0f172a", "text-halo-width": 1.8 } });
    const gf = { type: "FeatureCollection", features: Object.entries(gps).map(([k, v]) => ({ type: "Feature", geometry: { type: "Point", coordinates: [v.lon, v.lat] }, properties: { sta: k } })) };
    map.addSource("gps", { type: "geojson", data: gf });
    map.addLayer({ id: "gps", type: "circle", source: "gps", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 4, 14, 8], "circle-color": "#fde047", "circle-stroke-color": "#0f172a", "circle-stroke-width": 1.5 } });
    map.addLayer({ id: "gps-label", type: "symbol", source: "gps", minzoom: 10, layout: { "text-field": ["get", "sta"], "text-size": 10, "text-font": ["Noto Sans Bold"], "text-offset": [0, 1.2], "text-anchor": "top" }, paint: { "text-color": "#fef9c3", "text-halo-color": "#0f172a", "text-halo-width": 1.5 } });
    buildLegend2(); applyPubFilter();
    const h = decodeURIComponent(location.hash);
    if (/^#pub=/.test(h)) { const f = pubGeo.features.find(f => f.properties.well === h.slice(5)); if (f) { map.flyTo({ center: f.geometry.coordinates, zoom: 11 }); openPublic(f.properties.site_code); } }
    if (/^#1d=/.test(h)) { const f = dwrGeo.features.find(f => f.properties.site === h.slice(4)); if (f) { map.flyTo({ center: f.geometry.coordinates, zoom: 11 }); openDwr1d(f.properties.site); } }
    if (/^#gps=/.test(h)) { map.flyTo({ center: [gps[h.slice(5)].lon, gps[h.slice(5)].lat], zoom: 11 }); openGps(h.slice(5)); }
});

map.on("click", e => {
    if (map.getLayer("wells") && map.queryRenderedFeatures(e.point, { layers: ["wells"] }).length) return;      // analysis wells handled in app.js
    const f = map.queryRenderedFeatures(e.point, { layers: ["dwr1d", "pub-wells", "gps"].filter(l => map.getLayer(l)) })[0];
    if (!f) return;
    if (f.layer.id === "dwr1d") openDwr1d(f.properties.site); else if (f.layer.id === "pub-wells") openPublic(f.properties.site_code); else openGps(f.properties.sta);
});
["dwr1d", "pub-wells", "gps"].forEach(l => { map.on("mouseenter", l, () => map.getCanvas().style.cursor = "pointer"); map.on("mouseleave", l, () => map.getCanvas().style.cursor = ""); });

function buildLegend2(){
    const box = document.getElementById("legend-pub"); box.innerHTML = "";
    const row = (sw, t) => { const r = document.createElement("div"); r.className = "insar-legend-row"; r.innerHTML = sw + `<span>${t}</span>`; box.appendChild(r); };
    row(`<span class="conf-dot" style="background:${ZONE.Lower}"></span>`, "Well screened below Corcoran Clay");
    row(`<span class="conf-dot" style="background:${ZONE.Composite}"></span>`, "Screens span the clay (composite)");
    row(`<span class="conf-dot" style="background:${ZONE.Upper}"></span>`, "Above the clay");
    row(`<span class="conf-dot" style="background:${ZONE["No constr"]}"></span>`, "No construction data");
    row(`<span class="conf-dot ring" style="border-color:#fff"></span>`, "White ring = empirical estimate found");
    row(`<span class="conf-dot" style="background:${C_1D};border:2px solid #fff"></span>`, "DWR 1D-model critical head site");
    row(`<span class="conf-dot" style="background:#fde047"></span>`, "Continuous GPS station");
}
function applyPubFilter(){
    const m = document.getElementById("f-pub").value;
    const f = m === "lc" ? ["in", ["get", "zk"], ["literal", ["Lower", "Composite"]]] : m === "det" ? ["==", ["get", "det"], 1] : null;
    ["pub-wells", "pub-label"].forEach(l => { if (!map.getLayer(l)) return; const base = l === "pub-label" ? ["==", ["get", "det"], 1] : null; map.setFilter(l, f && base ? ["all", f, base] : f || base); });
}
document.getElementById("f-pub").addEventListener("change", applyPubFilter);
[["toggle-pub", ["pub-wells", "pub-label"]], ["toggle-1d", ["dwr1d", "dwr1d-label"]], ["toggle-gps", ["gps", "gps-label"]]].forEach(([id, ls]) =>
    document.getElementById(id).addEventListener("change", e => ls.forEach(l => map.getLayer(l) && map.setLayoutProperty(l, "visibility", e.target.checked ? "visible" : "none"))));

/* ── generic line/points panel (shared x-domain across stacked panels) ── */
const PW = 590, PL = 46, PR = 10;
function panel(o){
    const X = scale(o.x0, o.x1, PL, PW - PR), H = o.h, t = 18, b = o.axis ? 22 : 8;
    let vals = []; (o.lines || []).forEach(l => l.pts.forEach(p => vals.push(p[1]))); (o.dots || []).forEach(d => d.pts.forEach(p => vals.push(p[1]))); (o.hl || []).forEach(h => vals.push(h.y));
    let lo = Math.min(...vals, ...(o.incl || [])), hi = Math.max(...vals, ...(o.incl || [])); const pad = (hi - lo) * 0.1 || 1; lo -= pad; hi += pad;
    const Y = scale(lo, hi, H - b, t); let s = `<g transform="translate(0 ${o.oy})"><text class="ttl" x="${PL}" y="12">${o.title}</text>`;
    niceTicks(lo, hi, o.ticks || 4).forEach(v => { s += `<line x1="${PL}" x2="${PW - PR}" y1="${Y(v)}" y2="${Y(v)}" stroke="${v === 0 && o.zero ? "#64748b" : "#334155"}" stroke-width=".6"/><text x="${PL - 4}" y="${Y(v) + 3}" text-anchor="end">${fmt(v, o.dec == null ? 0 : o.dec)}</text>`; });
    const st = o.x1 - o.x0 > 60 ? 20 : o.x1 - o.x0 > 20 ? 5 : 1; for (let y = Math.ceil(o.x0 / st) * st; y <= o.x1; y += st) { s += `<line x1="${X(y)}" x2="${X(y)}" y1="${t}" y2="${H - b}" stroke="#334155" stroke-width=".6"/>`; if (o.axis) s += `<text x="${X(y)}" y="${H - 6}" text-anchor="middle">${y}</text>`; }
    (o.shade || []).forEach(q => { const a = Math.max(q[0], o.x0), z = Math.min(q[1], o.x1); if (z > a) s += `<rect x="${X(a)}" y="${t}" width="${X(z) - X(a)}" height="${H - b - t}" fill="${C_REB}" opacity=".16"/>`; });
    (o.hl || []).forEach(h => { s += `<line x1="${PL}" x2="${PW - PR}" y1="${Y(h.y)}" y2="${Y(h.y)}" stroke="${h.c}" stroke-width="${h.w || 1.6}" stroke-dasharray="${h.d || "6 3"}"/><text x="${h.right ? PW - PR - 2 : PL + 4}" y="${Y(h.y) + (h.dy || -4)}" text-anchor="${h.right ? "end" : "start"}" style="fill:${h.c};font-weight:600">${h.t}</text>`; });
    (o.lines || []).forEach(l => { const p = l.pts.filter(q => q[0] >= o.x0 - 0.01 && q[0] <= o.x1 + 0.1); s += `<polyline fill="none" stroke="${l.c}" stroke-width="${l.w || 1.6}" ${l.d ? `stroke-dasharray="${l.d}"` : ""} points="${p.map(q => X(q[0]).toFixed(1) + "," + Y(q[1]).toFixed(1)).join(" ")}"/>`; });
    (o.dots || []).forEach(d => { const p = d.pts.filter(q => q[0] >= o.x0 - 0.01); const many = p.length > 160;
        p.forEach(q => { s += `<circle cx="${X(q[0]).toFixed(1)}" cy="${Y(q[1]).toFixed(1)}" r="${many ? 1.4 : 3.4}" fill="${d.c}" ${many ? "" : `stroke="#1e293b" stroke-width="1.4" data-t="${fdate(q[0])}: ${fmt(q[1], 1)} ft"`}/>`; }); });
    return { svg: s + `</g>`, h: H };
}
function stack(ps, W = PW){ let y = 0, out = ""; ps.forEach(p => { p.oy = y; const r = panel(p); out += r.svg; y += r.h + 4; }); return `<svg class="chart" viewBox="0 0 ${W} ${y}" role="img">${out}</svg>`; }
function showDetail(html, hookW){
    document.getElementById("detail-body").innerHTML = html; document.getElementById("detail").classList.remove("hidden");
    let tip = document.querySelector(".chart-tip"); if (!tip) { tip = document.createElement("div"); tip.className = "chart-tip"; document.body.appendChild(tip); } tip.style.display = "none";
    document.querySelectorAll("#detail .chart circle[data-t]").forEach(c => {
        c.addEventListener("mouseenter", () => { tip.textContent = c.dataset.t; tip.style.display = "block"; });
        c.addEventListener("mousemove", e => { tip.style.left = e.clientX + 12 + "px"; tip.style.top = e.clientY - 28 + "px"; });
        c.addEventListener("mouseleave", () => tip.style.display = "none"); });
}
const prow = (k, v) => `<div class="pop-row"><span class="pop-k">${k}</span><span class="pop-v">${v}</span></div>`;
const legendRow = items => `<div class="d-legend">${items.map(i => `<span><i ${i.dot ? `class="dot" style="background:${i.c}"` : i.sw ? `class="sw" style="background:${i.c}"` : `style="border-color:${i.c};${i.d ? "border-top-style:dashed" : ""}"`}></i>${i.t}</span>`).join("")}</div>`;

/* ── public well detail ── */
let pubHist = false;
async function openPublic(sc){
    if (!pubFull) pubFull = await getJSON("data/empirical_wells.json");
    const w = pubFull[sc]; if (!w) return;
    const x0 = pubHist ? Math.floor(Math.min(w.gw[0][0], w.insar[0][0])) : Math.floor(w.insar[0][0]), x1 = Math.ceil(w.insar[w.insar.length - 1][0] + 0.05);
    const shade = (w.periods || []).map(p => [p.start, p.end]);
    const hl = []; if (w.emp_ch_latest != null) hl.push({ y: w.emp_ch_latest, c: C_EMP, t: `empirical critical head ${fmt(w.emp_ch_latest, 0)} ft` });
    if (w.comparable_1d) hl.push({ y: w.dwr1d_ch_2024, c: C_1D, t: `DWR 1D model (${esc(w.dwr1d_site)}) ${fmt(w.dwr1d_ch_2024, 0)} ft`, d: "2 3", dy: 12, right: true });
    if (pubHist) hl.push({ y: w.record_low_ft, c: C_RUN, t: `record low ${fmt(w.record_low_ft, 0)}`, d: "1 3", w: 1.2, right: true, dy: -3 });
    const chart = stack([
        { title: "Groundwater elevation (ft, NAVD88)", x0, x1, h: 180, dots: [{ pts: w.gw, c: "#38bdf8" }], lines: w.gw.length <= 160 ? [{ pts: w.gw, c: "#38bdf8", w: 1.2 }] : [], hl, shade },
        { title: "InSAR cumulative displacement (ft) · dashed = maximum subsidence to date", x0, x1, h: 125, axis: true, dec: 1, zero: true, ticks: 3,
          lines: [{ pts: w.insar, c: C_DISP, w: 1.8 }, { pts: w.runmin, c: C_RUN, w: 1.2, d: "4 3" }], shade }]);
    const c = { High: "#34d399", Moderate: "#fbbf24", Low: "#fb923c", "Not determinable": "#94a3b8" }[w.emp_conf];
    const hero = w.emp_ch_latest != null
        ? `<div class="d-hero"><div><div class="big">${fmt(w.emp_ch_latest, 0)} ft</div><div class="lab">empirical critical head (most recent rebound period) · NAVD88</div></div><div><span class="badge" style="background:${c}">${w.emp_conf} confidence</span></div>` +
          `<div><div class="big" style="font-size:18px;color:${w.latest_ft >= w.emp_ch_latest ? "#34d399" : "#f87171"}">${w.latest_ft >= w.emp_ch_latest ? "+" : "−"}${fmt(Math.abs(w.latest_ft - w.emp_ch_latest), 0)} ft</div><div class="lab">latest level vs estimate</div></div></div>`
        : `<div class="d-hero"><div class="big" style="font-size:18px">No empirical estimate — no land-surface rebound</div><span class="badge" style="background:${c}">Not determinable</span></div>`;
    const per = (w.periods || []).map(p => `${fdate(p.start)}–${fdate(p.end)}: low ${fmt(p.low, 0)} ft (${p.months} mo, ${p.n_obs} readings, rebound ${fmt(p.rebound_ft, 2)} ft)`).join("<br>");
    const g = [prow("Aquifer position", esc(w.zone) + (w.zone_ambiguous ? " · <i>ambiguous (screen within 60 ft of clay)</i>" : "")),
        prow("Screen / well depth (ft)", `${w.top_prf_ft && w.bot_prf_ft ? esc(w.top_prf_ft) + "–" + esc(w.bot_prf_ft) : "—"} / ${esc(w.well_depth_ft || "—")}`),
        prow("Corcoran Clay (ft bgs)", `${w.clay_top_ft}–${w.clay_bot_ft} · ${esc(w.clay_ref_site)}`), prow("Program", esc(w.program)),
        prow("Record", `${esc(w.first)} → ${esc(w.last)} (${w.n}; ${w.n_since_2015} since 2015)`), prow("Record low / latest", `${fmt(w.record_low_ft, 0)} / ${fmt(w.latest_ft, 0)} ft`),
        prow("InSAR since Jun 2015", `${fmt(w.insar_total_ft, 2)} ft`), prow("Last 2 yr rate", `${fmt(w.recent_rate_ftyr, 2)} ft/yr`),
        prow("Rebound periods", `${w.n_periods} (${w.rebound_months} months)`), prow("Nearest DWR 1D site", `${esc(w.dwr1d_site)} · ${w.dwr1d_km} km · CH ${fmt(w.dwr1d_ch_2024, 0)} ft`)];
    let note = w.emp_ch_latest == null ? "InSAR shows no sustained elastic rebound (≥0.067 ft above the maximum-subsidence line) at this location, so the empirical method (BMP §5.3.2) cannot bound critical head here. BMP §5.3.4: use modeling." :
        `Lowest groundwater level during each rebound period — BMP §5.3.2. ${w.emp_conf === "High" ? "" : "Few independent periods / readings: treat as approximate."}`;
    if (w.comparable_1d && w.diff_vs_1d != null) note += ` Nearest DWR 1D model in the same head regime differs by ${w.diff_vs_1d > 0 ? "+" : "−"}${fmt(Math.abs(w.diff_vs_1d), 0)} ft.`;
    else if (w.emp_ch_latest != null) note += " The nearest DWR 1D site is in a different head regime, so the values are not directly comparable.";
    showDetail(`<div class="d-title">${esc(w.well)}</div><div class="d-sub">Public well (DWR periodic GWL data) · ${esc(w.basin)} · Station ${esc(w.site_code)}</div>${hero}${chart}` +
        legendRow([{ c: "#38bdf8", t: "groundwater elevation" }, { c: C_RUN, t: "maximum subsidence to date", d: 1 }, { c: C_REB, t: "rebound periods", sw: 1 }, { c: C_EMP, t: "empirical estimate", d: 1 }, { c: C_1D, t: "1D model CH (comparable sites)", d: 1 }]) +
        `<div class="d-grid">${g.join("")}</div>${per ? `<div class="d-note" style="border-left-color:#34d399">${per}</div>` : ""}<div class="d-note">${note}</div>` +
        `<div class="d-tools"><button id="btn-hist2">${pubHist ? "Show InSAR era only" : "Show full groundwater history"}</button></div>`);
    document.getElementById("btn-hist2").onclick = () => { pubHist = !pubHist; openPublic(sc); };
}

/* ── DWR 1D model site detail ── */
async function openDwr1d(site){
    if (!dwrSeries) dwrSeries = await getJSON("data/dwr_1d_ch_series.json");
    const p = dwrProps[site] || {};
    const s = dwrSeries[site] || {}, x1 = 2025;
    const ch = s.ch || [], ob = s.obs_lower || [];
    const x0 = Math.floor(Math.min(ch.length ? ch[0][0] : 2000, ob.length ? ob[0][0] : 2000, 1950));
    const chart = stack([{ title: "Lower aquifer: model critical head (line) vs observed heads (dots), ft NAVD88", x0, x1, h: 230, axis: true, lines: ch.length ? [{ pts: ch, c: C_1D, w: 2 }] : [], dots: ob.length ? [{ pts: ob, c: "#38bdf8" }] : [] }]);
    const rows = [prow("Subbasin / GSA", `${esc(p.subbasin)} · ${esc(p.gsa)}`), prow("Model layer", esc(p.ch_layer)),
        prow("Critical head 2015 → 2020 → 2024", `${fmt(p.ch_2015, 0)} → ${fmt(p.ch_2020, 0)} → ${fmt(p.ch_2024, 0)} ft`),
        prow("Corcoran Clay (ft bgs)", p.corcoran_top_ft ? `${p.corcoran_top_ft}–${p.corcoran_bot_ft}` : "—"), prow("Model depth (ft)", fmt(p.total_depth_ft, 0)),
        prow("Observed lower-aquifer low", `${fmt(p.obs_lower_low, 0)} ft (${fmt(p.obs_lower_lowyr, 0)})`), prow("Observed lower median since 2015", `${fmt(p.obs_lower_med2015on, 0)} ft`)];
    showDetail(`<div class="d-title">DWR 1D model site ${esc(site)}</div><div class="d-sub">MODFLOW 6-CSUB · ensemble-mean critical head (DWR / INTERA, Dec 2025)</div>` +
        `<div class="d-hero"><div><div class="big">${fmt(p.ch_2024, 0)} ft</div><div class="lab">calibrated critical head, 2024 · lower aquifer · NAVD88</div></div></div>${chart}` +
        legendRow([{ c: C_1D, t: "model critical head (preconsolidation head)" }, { c: "#38bdf8", t: "observed lower-aquifer heads", dot: 1 }]) + `<div class="d-grid">${rows.join("")}</div>` +
        `<div class="d-note">System-level ensemble mean from DWR's published 1D models. Critical head is often <b>higher</b> than the lowest observed level because of delayed equilibration of clay interbeds. Forecast scenarios after 2024 are not shown.</div>`);
}

/* ── GPS detail ── */
function openGps(sta){
    const g = gpsData[sta]; if (!g) return;
    const base = g.gps.length ? g.gps[g.gps.length - 1] : null; const gi = g.gps; const a = 2015.45;
    const gv = k => { let b = gi[0]; for (const p of gi) if (Math.abs(p[0] - k) < Math.abs(b[0] - k)) b = p; return b[1]; };
    const rebased = gi.filter(p => p[0] >= a).map(p => [p[0], +(p[1] - gv(Math.max(a, gi[0][0]))).toFixed(3)]);
    const x1 = Math.ceil(Math.max(g.insar.length ? g.insar[g.insar.length - 1][0] : 2026, rebased.length ? rebased[rebased.length - 1][0] : 2026) + 0.05);
    const chart = stack([{ title: "Vertical displacement since mid-2015 (ft; negative = subsidence)", x0: 2015, x1, h: 220, axis: true, dec: 1, zero: true, ticks: 4, lines: [{ pts: rebased, c: "#fde047", w: 1.6 }, { pts: g.insar, c: C_DISP, w: 1.8 }] }]);
    showDetail(`<div class="d-title">GPS station ${esc(sta)}</div><div class="d-sub">Continuous GPS (Nevada Geodetic Lab / EarthScope) vs DWR InSAR sampled at the station</div>${chart}` +
        legendRow([{ c: "#fde047", t: "GPS (rebased to mid-2015)" }, { c: C_DISP, t: "InSAR at station" }]) +
        `<div class="d-note" style="border-left-color:#fde047">Used to validate InSAR near the towns: see data/gps_validation.csv — over ~10 yr InSAR agrees with GPS within 0.1 ft at Hanford (CAHA), 0.33 ft at Lemoore (LEMA) and 0.47 ft at Corcoran (CRCN), slightly under-reading the sinking at the two biggest-subsidence towns.</div>`);
}
