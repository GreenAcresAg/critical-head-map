/* ══════════════════════════════════════════════════════════════════
   Critical Head Map — Green Acres Consulting, Inc.
   Trend-based critical-head estimates (DWR Land Subsidence BMP, Jan 2026, §5.3.1)
   for monitoring wells in the Mid-Kings River & South Fork Kings GSAs (Tulare Lake subbasin).
   Shell adapted from the InSAR Land Subsidence Map (MapLibre GL).
   Results are precomputed by analyze_trend.py → data/critical_head.json
   ══════════════════════════════════════════════════════════════════ */
const SVC = "https://gis.water.ca.gov/arcgisimg/rest/services/SAR/Vertical_Displacement_TRE_ALTAMIRA_Total_Since_20150613_Mosaic/ImageServer";
const TARGET = ["Mid-Kings River GSA", "South Fork Kings GSA"];
const CONF = { "High": "#34d399", "Moderate": "#fbbf24", "Low": "#fb923c", "Not determinable": "#94a3b8" };
const C_GW = "#38bdf8", C_DISP = "#f472b6", C_CH = "#f87171", C_QUIET = "#34d399";
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

let map, wells = {}, geo;
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = (v, d = 1) => v == null ? "—" : (+v).toFixed(d).replace(/^-/, "−");
const fdate = y => { const yr = Math.floor(y), m = Math.min(11, Math.floor((y - yr) * 12)); return `${MON[m]} ${yr}`; };
async function getJSON(u, opt){ const r = await fetch(u, opt); if (!r.ok) throw new Error(u + " " + r.status); return r.json(); }

/* ── Map ─────────────────────────────────────────────────────────── */
map = new maplibregl.Map({
    container: "map",
    style: {
        version: 8,
        sources: {
            satellite: { type: "raster", tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, attribution: "Esri, Maxar, Earthstar Geographics · InSAR: CA DWR / TRE ALTAMIRA · Wells: DWR SGMA Portal", maxzoom: 19 },
            labels: { type: "raster", tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, maxzoom: 19 },
            roads: { type: "raster", tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, maxzoom: 19 },
        },
        glyphs: "vendor/fonts/{fontstack}/{range}.pbf",
        layers: [
            { id: "satellite", type: "raster", source: "satellite" },
            { id: "roads", type: "raster", source: "roads", paint: { "raster-opacity": 0.8 } },
            { id: "labels", type: "raster", source: "labels", paint: { "raster-opacity": 0.7 } },
        ],
    },
    center: [-119.72, 36.30], zoom: 9.6, maxZoom: 16,
});
map.addControl(new maplibregl.NavigationControl(), "top-right");

map.on("load", async () => {
    await Promise.all([loadData(), loadInsar()]);
    addGSAs(); addWells(); buildLegend(); applyFilters();
    const h = decodeURIComponent(location.hash.replace('#well=', '')); const hit = Object.values(wells).find(w => w.well === h); if (hit) { openDetail(hit.stn_id); map.flyTo({ center: [hit.lon, hit.lat], zoom: 11 }); }   // deep link: #well=KRCDAC3D
});

async function loadData(){
    wells = await getJSON("data/critical_head.json");
    geo = await getJSON("data/critical_head_wells.geojson");
}

/* ── InSAR overlay: latest cumulative raster, live from DWR ──────── */
async function loadInsar(){
    try {
        const j = await getJSON(`${SVC}/query?where=1%3D1&outFields=OBJECTID,DateTo&returnGeometry=false&orderByFields=DateTo+DESC&resultRecordCount=1&f=json`);
        const f = j.features[0].attributes;
        const mr = encodeURIComponent(JSON.stringify({ mosaicMethod: "esriMosaicLockRaster", lockRasterIds: [f.OBJECTID] }));
        map.addSource("insar", { type: "raster", tileSize: 256, tiles: [`${SVC}/exportImage?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png&transparent=true&f=image&mosaicRule=${mr}`] });
        map.addLayer({ id: "insar", type: "raster", source: "insar", paint: { "raster-opacity": 0.65 } }, "labels");
        const d = new Date(f.DateTo); document.getElementById("insar-date").textContent = `cumulative since Jun 2015, thru ${MON[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
        const lg = await getJSON(`${SVC}/legend?f=json`);
        const box = document.getElementById("insar-legend");
        ((lg.layers && lg.layers[0] && lg.layers[0].legend) || []).forEach(it => {
            const r = document.createElement("div"); r.className = "insar-legend-row";
            r.innerHTML = `<img class="insar-swatch" src="data:${it.contentType};base64,${it.imageData}" alt=""><span>${esc(it.label)} ft</span>`; box.appendChild(r);
        });
    } catch (e) { document.getElementById("insar-date").textContent = "unavailable"; }
}
document.getElementById("toggle-insar").addEventListener("change", e => map.getLayer("insar") && map.setLayoutProperty("insar", "visibility", e.target.checked ? "visible" : "none"));
document.getElementById("insar-op").addEventListener("input", e => map.getLayer("insar") && map.setPaintProperty("insar", "raster-opacity", e.target.value / 100));

/* ── GSA boundaries (target GSAs emphasised) ─────────────────────── */
async function addGSAs(){
    const g = await getJSON("data/surrounding_gsas_detail.geojson");
    const isT = ["in", ["get", "GSA_Name"], ["literal", TARGET]];
    map.addSource("gsas", { type: "geojson", data: g });
    map.addLayer({ id: "gsas-fill", type: "fill", source: "gsas", filter: isT, paint: { "fill-color": "#f43f5e", "fill-opacity": 0.07 } }, "labels");
    map.addLayer({ id: "gsas-line", type: "line", source: "gsas", paint: {
        "line-color": ["case", isT, "#fb7185", "#cbd5e1"], "line-width": ["case", isT, 2.4, 0.8], "line-opacity": ["case", isT, 0.95, 0.5] } });
    const pts = { type: "FeatureCollection", features: g.features.filter(f => TARGET.includes(f.properties.GSA_Name)).map(f => { const c = turf.centroid(f); c.properties = { n: f.properties.GSA_Name }; return c; }) };
    map.addSource("gsa-lab", { type: "geojson", data: pts });
    map.addLayer({ id: "gsas-label", type: "symbol", source: "gsa-lab", layout: { "text-field": ["get", "n"], "text-size": 12, "text-font": ["Noto Sans Bold"], "text-max-width": 8 },
        paint: { "text-color": "#fff", "text-halo-color": "#0f172a", "text-halo-width": 1.8 } });
    document.getElementById("toggle-gsa").addEventListener("change", e => ["gsas-fill","gsas-line","gsas-label"].forEach(l => map.setLayoutProperty(l, "visibility", e.target.checked ? "visible" : "none")));
}

/* ── Wells ───────────────────────────────────────────────────────── */
const confMatch = () => { const m = ["match", ["get", "confidence"]]; for (const [k, v] of Object.entries(CONF)) m.push(k, v); m.push("#94a3b8"); return m; };
function addWells(){
    map.addSource("wells", { type: "geojson", data: geo });
    const ring = ["==", ["get", "basis"], "Upper bound only"];
    map.addLayer({ id: "wells-halo", type: "circle", source: "wells", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 8, 14, 15], "circle-color": "#0f172a", "circle-opacity": 0.75 } });
    map.addLayer({ id: "wells", type: "circle", source: "wells", paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 5.5, 14, 11],
        "circle-color": ["case", ring, "rgba(0,0,0,0)", confMatch()],
        "circle-stroke-color": confMatch(), "circle-stroke-width": ["case", ring, 3, 1.5] } });
    map.addLayer({ id: "wells-label", type: "symbol", source: "wells", minzoom: 11, layout: {
        "text-field": ["concat", ["get", "well"], ["case", ["has", "est_ft"], ["concat", "\n", ["to-string", ["get", "est_ft"]], " ft"], ""]],
        "text-size": 10.5, "text-font": ["Noto Sans Bold"], "text-offset": [0, 1.7], "text-anchor": "top", "text-optional": true },
        paint: { "text-color": "#fff", "text-halo-color": "#0f172a", "text-halo-width": 1.6 } });
    map.on("click", "wells", e => openDetail(e.features[0].properties.stn_id));
    map.on("mouseenter", "wells", () => map.getCanvas().style.cursor = "pointer");
    map.on("mouseleave", "wells", () => map.getCanvas().style.cursor = "");
}
function buildLegend(){
    const box = document.getElementById("legend-conf");
    const txt = { "High": "High confidence", "Moderate": "Moderate", "Low": "Low", "Not determinable": "Not determinable by trend" };
    for (const [k, c] of Object.entries(CONF)) {
        const r = document.createElement("div"); r.className = "insar-legend-row";
        r.innerHTML = `<span class="conf-dot" style="background:${c}"></span><span>${txt[k]}</span>`; box.appendChild(r);
    }
    const r = document.createElement("div"); r.className = "insar-legend-row";
    r.innerHTML = `<span class="conf-dot ring" style="border-color:#e2e8f0"></span><span>Upper bound only (hollow)</span>`; box.appendChild(r);
}

/* ── Filters + summary ───────────────────────────────────────────── */
function passes(w){
    const g = document.getElementById("f-gsa").value, a = document.getElementById("f-aq").value;
    if (g && w.gsa !== g) return false;
    if (a && !w.representativeness.startsWith(a)) return false;
    if (document.getElementById("f-hide-nd").checked && w.confidence === "Not determinable") return false;
    return true;
}
function applyFilters(){
    const ids = Object.values(wells).filter(passes).map(w => w.stn_id);
    const f = ["in", ["get", "stn_id"], ["literal", ids]];
    ["wells-halo", "wells", "wells-label"].forEach(l => map.setFilter(l, f));
    renderSummary();
}
["f-gsa", "f-aq", "f-hide-nd"].forEach(id => document.getElementById(id).addEventListener("change", applyFilters));
function renderSummary(){
    const box = document.getElementById("summary"); box.innerHTML = "";
    TARGET.forEach(g => {
        const ws = Object.values(wells).filter(w => w.gsa === g && passes(w));
        if (!ws.length) return;
        const det = ws.filter(w => w.est_ft != null), bra = det.filter(w => w.basis === "Bracketed");
        const rng = a => a.length ? `${fmt(Math.min(...a.map(w => w.est_ft)), 0)} to ${fmt(Math.max(...a.map(w => w.est_ft)), 0)} ft` : "—";
        const d = document.createElement("div"); d.className = "sum-gsa";
        d.innerHTML = `<b>${esc(g)}</b>` +
            `<div class="sum-row"><span>Screened wells</span><span>${ws.length}</span></div>` +
            `<div class="sum-row"><span>Estimate determined</span><span>${det.length}</span></div>` +
            `<div class="sum-row"><span>&nbsp;&nbsp;bracketed</span><span>${bra.length}</span></div>` +
            `<div class="sum-row"><span>&nbsp;&nbsp;upper bound only</span><span>${det.length - bra.length}</span></div>` +
            `<div class="sum-row"><span>Not determinable</span><span>${ws.length - det.length}</span></div>` +
            `<div class="sum-row"><span>Bracketed range (NAVD88)</span><span>${rng(bra)}</span></div>`;
        box.appendChild(d);
    });
}

/* ── Detail panel: two stacked panels, shared time axis (no dual axis) ── */
let fullHist = false, curId = null;
function scale(d0, d1, r0, r1){ return v => r0 + (v - d0) / (d1 - d0) * (r1 - r0); }
function niceTicks(lo, hi, n = 4){
    const span = hi - lo, raw = span / n, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p;
    const st = (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p, out = [];
    for (let v = Math.ceil(lo / st) * st; v <= hi + 1e-9; v += st) out.push(+v.toFixed(6));
    return out;
}
function chartSVG(w){
    const W = 590, pl = 46, pr = 10, x0 = fullHist ? Math.floor(Math.min(w.gw[0][0], w.insar[0][0])) : Math.floor(w.insar[0][0]);
    const x1 = Math.ceil(w.insar[w.insar.length - 1][0] + 0.05);
    const X = scale(x0, x1, pl, W - pr);
    const gw = w.gw.filter(p => p[0] >= x0 - 0.01);
    const H1 = 190, t1 = 18, b1 = 8, H2 = 120, t2 = 18, b2 = 22;
    let g = gw.map(p => p[1]); const ch = w.est_ft, lo = w.hist_low_ft;
    if (ch != null) g.push(ch); if (lo != null && fullHist) g.push(lo);
    let ymin = Math.min(...g), ymax = Math.max(...g), pad = (ymax - ymin) * 0.1 || 5; ymin -= pad; ymax += pad;
    const Y1 = scale(ymin, ymax, H1 - b1, t1);
    const di = w.insar.map(p => p[1]), dmin = Math.min(...di, 0) - 0.15, dmax = Math.max(...di, 0) + 0.1;
    const Y2 = scale(dmin, dmax, H2 - b2, t2);
    const yrTicks = []; const step = x1 - x0 > 20 ? 5 : 1; for (let y = Math.ceil(x0 / step) * step; y <= x1; y += step) yrTicks.push(y);
    const quiet = (w.quiet_windows || []).map(([a, b]) => ({ a: Math.max(a, x0), b: Math.min(b, x1) })).filter(q => q.b > q.a);
    const sel = w.est_ft != null ? [w.win_start, w.win_end] : null;
    let s = `<svg class="chart" viewBox="0 0 ${W} ${H1 + H2 + 6}" role="img" aria-label="Groundwater elevation and InSAR displacement for ${esc(w.well)}">`;
    // top panel
    s += `<text class="ttl" x="${pl}" y="12">Groundwater elevation (ft, NAVD88)</text>`;
    niceTicks(ymin, ymax).forEach(v => { s += `<line x1="${pl}" x2="${W - pr}" y1="${Y1(v)}" y2="${Y1(v)}" stroke="#334155" stroke-width=".6"/><text x="${pl - 4}" y="${Y1(v) + 3}" text-anchor="end">${fmt(v, 0)}</text>`; });
    yrTicks.forEach(y => { s += `<line x1="${X(y)}" x2="${X(y)}" y1="${t1}" y2="${H1 - b1}" stroke="#334155" stroke-width=".6"/>`; });
    quiet.forEach(q => { s += `<rect x="${X(q.a)}" y="${t1}" width="${X(q.b) - X(q.a)}" height="${H1 - b1 - t1}" fill="${C_QUIET}" opacity=".13"/>`; });
    if (sel) s += `<rect x="${X(Math.max(sel[0], x0))}" y="${t1}" width="${X(Math.min(sel[1], x1)) - X(Math.max(sel[0], x0))}" height="${H1 - b1 - t1}" fill="none" stroke="${C_QUIET}" stroke-width="1.4" stroke-dasharray="4 3"/>`;
    if (fullHist && lo != null) s += `<line x1="${pl}" x2="${W - pr}" y1="${Y1(lo)}" y2="${Y1(lo)}" stroke="#94a3b8" stroke-dasharray="1 3" stroke-width="1.2"/><text class="lab-lo" x="${W - pr - 2}" y="${Y1(lo) - 3}" text-anchor="end">record low ${fmt(lo, 0)}</text>`;
    if (ch != null) s += `<line x1="${pl}" x2="${W - pr}" y1="${Y1(ch)}" y2="${Y1(ch)}" stroke="${C_CH}" stroke-width="1.8" stroke-dasharray="6 3"/><text class="lab-ch" x="${pl + 4}" y="${Y1(ch) - 4}">${w.basis === "Bracketed" ? "critical head est." : "upper bound"} ${fmt(ch, 0)} ft</text>`;
    s += `<polyline fill="none" stroke="${C_GW}" stroke-width="1.5" points="${gw.map(p => X(p[0]).toFixed(1) + "," + Y1(p[1]).toFixed(1)).join(" ")}"/>`;
    gw.forEach(p => { const inq = sel && p[0] >= sel[0] && p[0] <= sel[1];
        s += `<circle cx="${X(p[0]).toFixed(1)}" cy="${Y1(p[1]).toFixed(1)}" r="3.6" fill="${C_GW}" stroke="#1e293b" stroke-width="1.5" data-t="${fdate(p[0])}: ${fmt(p[1], 1)} ft${inq ? " (in quiet window)" : ""}"/>`; });
    // bottom panel
    const oy = H1 + 6;
    s += `<g transform="translate(0 ${oy})"><text class="ttl" x="${pl}" y="12">InSAR cumulative vertical displacement at well (ft; negative = subsidence)</text>`;
    niceTicks(dmin, dmax, 3).forEach(v => { s += `<line x1="${pl}" x2="${W - pr}" y1="${Y2(v)}" y2="${Y2(v)}" stroke="${v === 0 ? "#64748b" : "#334155"}" stroke-width="${v === 0 ? 1 : .6}"/><text x="${pl - 4}" y="${Y2(v) + 3}" text-anchor="end">${fmt(v, 1)}</text>`; });
    yrTicks.forEach(y => { s += `<line x1="${X(y)}" x2="${X(y)}" y1="${t2}" y2="${H2 - b2}" stroke="#334155" stroke-width=".6"/><text x="${X(y)}" y="${H2 - 6}" text-anchor="middle">${y}</text>`; });
    quiet.forEach(q => { s += `<rect x="${X(q.a)}" y="${t2}" width="${X(q.b) - X(q.a)}" height="${H2 - b2 - t2}" fill="${C_QUIET}" opacity=".13"/>`; });
    if (sel) s += `<rect x="${X(Math.max(sel[0], x0))}" y="${t2}" width="${X(Math.min(sel[1], x1)) - X(Math.max(sel[0], x0))}" height="${H2 - b2 - t2}" fill="none" stroke="${C_QUIET}" stroke-width="1.4" stroke-dasharray="4 3"/>`;
    s += `<polyline fill="none" stroke="${C_DISP}" stroke-width="1.8" points="${w.insar.map(p => X(p[0]).toFixed(1) + "," + Y2(p[1]).toFixed(1)).join(" ")}"/>`;
    // hover catcher
    s += `<rect class="hov" x="${pl}" y="${t2}" width="${W - pl - pr}" height="${H2 - b2 - t2}" fill="transparent"/></g></svg>`;
    return s;
}
function lookupDisp(w, y){ const a = w.insar; let best = a[0]; for (const p of a) if (Math.abs(p[0] - y) < Math.abs(best[0] - y)) best = p; return best; }

function openDetail(id){
    const w = wells[id]; if (!w) return; curId = id;
    const c = CONF[w.confidence];
    const row = (k, v) => `<div class="pop-row"><span class="pop-k">${k}</span><span class="pop-v">${v}</span></div>`;
    const dtw = w.est_dtw_ft != null ? `${fmt(w.est_dtw_ft, 0)} ft below ground` : "";
    let hero;
    if (w.est_ft != null) {
        hero = `<div class="d-hero"><div><div class="big">${fmt(w.est_ft, 0)} ft</div><div class="lab">${w.basis === "Bracketed" ? "critical head estimate" : "critical head ≤ (upper bound)"} · NAVD88${dtw ? " · " + dtw : ""}</div></div>` +
            `<div><span class="badge" style="background:${c}">${esc(w.confidence)} confidence</span></div>` +
            `<div><div class="big" style="font-size:18px;color:${w.status === "Above estimate" ? "#34d399" : "#f87171"}">${w.cushion_ft >= 0 ? "+" : "−"}${fmt(Math.abs(w.cushion_ft), 0)} ft</div><div class="lab">latest level (${esc(w.latest_date)}) vs estimate — ${w.status.toLowerCase()}</div></div></div>`;
    } else {
        hero = `<div class="d-hero"><div><div class="big" style="font-size:18px">Not determinable by trend</div></div><span class="badge" style="background:${c}">No estimate</span></div>`;
    }
    const grid = [
        row("GSA", esc(w.gsa)), row("Aquifer position", esc(w.representativeness)), row("Aquifer (DWR)", esc(w.aquifer)),
        row("Well / perforations (ft)", `${esc(w.well_depth_ft || "—")} / ${w.top_perf_ft && w.bot_perf_ft ? esc(w.top_perf_ft) + "–" + esc(w.bot_perf_ft) : "—"}`),
        row("Ground elev. (ft)", fmt(w.gse_ft, 1)), row("GW record", `${esc(w.gw_first)} → ${esc(w.gw_last)} (${w.n_total})`),
        row("InSAR since Jun 2015", `${fmt(w.insar_total_ft, 2)} ft`), row("Last 2 yr rate", `${fmt(w.recent_rate_ftyr, 2)} ft/yr`),
        row("Record-low level", `${fmt(w.hist_low_ft, 0)} ft`), row("Latest level", `${fmt(w.latest_ft, 0)} ft`),
    ];
    if (w.est_ft != null) grid.push(row("Quiet window", `${fdate(w.win_start)} – ${fdate(w.win_end)}`), row("Readings in window", w.win_n),
        row(`Estimate @ ${w.thr_ft === 0.067 ? "0.10" : "0.067"} ft threshold`, w.sens_est_ft != null ? fmt(w.sens_est_ft, 0) + " ft" : "—"),
        row("Active-subsidence readings", `${w.active_n} (${w.active_above_est} above estimate)`));
    const note = w.notes ? `<div class="d-note">${esc(w.notes)}</div>` : "";
    const tbl = w.est_ft != null ? "" : "";
    document.getElementById("detail-body").innerHTML =
        `<div class="d-title">${esc(w.well)}</div><div class="d-sub">DWR SGMA monitoring well · Station ${esc(w.stn_id)} · GW data grade ${esc(w.grade)}</div>${hero}` +
        chartSVG(w) +
        `<div class="d-legend"><span><i style="border-color:${C_GW}"></i>groundwater elevation</span><span><i class="dot" style="background:${C_GW}"></i>measurement</span>` +
        `<span><i style="border-color:${C_CH};border-top-style:dashed"></i>${w.est_ft != null ? "estimate" : "—"}</span><span><i class="sw" style="background:${C_QUIET}"></i>sustained minimal-subsidence windows</span><span><i style="border-color:${C_DISP}"></i>InSAR</span></div>` +
        `<div class="d-grid">${grid.join("")}</div>${note}` +
        `<div class="d-tools"><button id="btn-hist">${fullHist ? "Show InSAR era only" : "Show full groundwater history"}</button><button id="btn-csv">Download well CSV</button></div>`;
    document.getElementById("detail").classList.remove("hidden");
    document.getElementById("btn-hist").onclick = () => { fullHist = !fullHist; openDetail(id); };
    document.getElementById("btn-csv").onclick = () => downloadCSV(w);
    wireHover(w);
}
function wireHover(w){
    const svg = document.querySelector("#detail .chart"); if (!svg) return;
    let tip = document.querySelector(".chart-tip"); if (!tip) { tip = document.createElement("div"); tip.className = "chart-tip"; document.body.appendChild(tip); }
    tip.style.display = "none";
    svg.querySelectorAll("circle[data-t]").forEach(c => {
        c.addEventListener("mouseenter", () => { tip.textContent = c.dataset.t; tip.style.display = "block"; });
        c.addEventListener("mousemove", e => { tip.style.left = e.clientX + 12 + "px"; tip.style.top = e.clientY - 28 + "px"; });
        c.addEventListener("mouseleave", () => tip.style.display = "none");
    });
    const hov = svg.querySelector(".hov"), x0 = fullHist ? Math.floor(Math.min(w.gw[0][0], w.insar[0][0])) : Math.floor(w.insar[0][0]), x1 = Math.ceil(w.insar[w.insar.length - 1][0] + 0.05);
    hov.addEventListener("mousemove", e => {
        const r = svg.getBoundingClientRect(), k = 590 / r.width, px = (e.clientX - r.left) * k, y = x0 + (px - 46) / (590 - 56) * (x1 - x0);
        const p = lookupDisp(w, y); tip.textContent = `${fdate(p[0])}: ${fmt(p[1], 2)} ft cumulative`; tip.style.display = "block";
        tip.style.left = e.clientX + 12 + "px"; tip.style.top = e.clientY - 28 + "px";
    });
    hov.addEventListener("mouseleave", () => tip.style.display = "none");
}
function downloadCSV(w){
    const lines = ["type,decimal_year,value_ft"].concat(w.gw.map(p => `groundwater_elevation_navd88,${p[0]},${p[1]}`), w.insar.map(p => `insar_cumulative_displacement,${p[0]},${p[1]}`));
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" })); a.download = `${w.well.replace(/\W+/g, "_")}_critical_head_series.csv`; a.click();
}
document.getElementById("detail-close").addEventListener("click", () => document.getElementById("detail").classList.add("hidden"));

/* ── Basemap / fullscreen / sidebar (shared shell) ───────────────── */
const BASEMAPS = {
    satellite: { tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], labels: false },
    hybrid: { tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], labels: true },
    usgs: { tiles: ["https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}"], labels: false },
    streets: { tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], labels: false },
};
let currentBasemap = "hybrid";
document.getElementById("basemap-btn").addEventListener("click", () => document.getElementById("basemap-menu").classList.toggle("hidden"));
document.addEventListener("click", e => { if (!e.target.closest(".basemap-selector")) document.getElementById("basemap-menu").classList.add("hidden"); });
document.querySelectorAll(".basemap-option").forEach(opt => opt.addEventListener("click", () => {
    const id = opt.dataset.basemap; if (id === currentBasemap) return; currentBasemap = id; const bm = BASEMAPS[id];
    const src = map.getSource("satellite"); if (src) src.setTiles(bm.tiles);
    ["labels", "roads"].forEach(l => { if (map.getLayer(l)) map.setLayoutProperty(l, "visibility", bm.labels ? "visible" : "none"); });
    document.querySelectorAll(".basemap-option").forEach(o => o.classList.remove("active")); opt.classList.add("active"); document.getElementById("basemap-menu").classList.add("hidden");
}));
document.getElementById("fullscreen-btn").addEventListener("click", () => {
    if (document.fullscreenElement) return document.exitFullscreen();
    document.documentElement.requestFullscreen().catch(() => window.open(location.href, "_blank"));
});
document.addEventListener("fullscreenchange", () => {
    const f = !!document.fullscreenElement; document.getElementById("fs-expand").style.display = f ? "none" : "block"; document.getElementById("fs-collapse").style.display = f ? "block" : "none"; setTimeout(() => map.resize(), 100);
});
const sidebar = document.getElementById("sidebar"), sbt = document.getElementById("sidebar-toggle");
sbt.addEventListener("click", () => { sidebar.classList.toggle("sidebar-closed"); sidebar.classList.toggle("sidebar-open"); setTimeout(() => map.resize(), 300); });
function fit(){ if (innerWidth < 900) { sbt.classList.add("visible"); sidebar.classList.replace("sidebar-open", "sidebar-closed"); } else { sbt.classList.remove("visible"); sidebar.classList.replace("sidebar-closed", "sidebar-open"); } setTimeout(() => map.resize(), 300); }
fit(); addEventListener("resize", () => { clearTimeout(fit.t); fit.t = setTimeout(fit, 200); });
