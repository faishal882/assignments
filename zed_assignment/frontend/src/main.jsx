import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import maplibregl from "maplibre-gl";
import { Check, Minus, Plus, RotateCcw, Trash2, X } from "lucide-react";
import "maplibre-gl/dist/maplibre-gl.css";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const EMPTY_COLLECTION = { type: "FeatureCollection", features: [] };

const BASE_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

function asCollection(value) {
  if (!value) return EMPTY_COLLECTION;
  return value.type === "FeatureCollection" ? value : { type: "FeatureCollection", features: [value] };
}

function boundsFor(feature) {
  const bounds = new maplibregl.LngLatBounds();
  let found = false;
  const visit = (coordinates) => {
    if (!Array.isArray(coordinates)) return;
    if (typeof coordinates[0] === "number") {
      bounds.extend(coordinates);
      found = true;
      return;
    }
    coordinates.forEach(visit);
  };
  visit(feature?.geometry?.coordinates);
  return found ? bounds : null;
}

function polygonFrom(points) {
  const coordinates = points.map(({ lng, lat }) => [lng, lat]);
  coordinates.push(coordinates[0]);
  return { type: "Polygon", coordinates: [coordinates] };
}

function draftGeoJSON(points) {
  const features = points.map((point, index) => ({
    type: "Feature",
    properties: { index },
    geometry: { type: "Point", coordinates: [point.lng, point.lat] },
  }));
  if (points.length > 1) {
    features.push({
      type: "Feature",
      properties: { draftLine: true },
      geometry: { type: "LineString", coordinates: points.map(({ lng, lat }) => [lng, lat]) },
    });
  }
  return { type: "FeatureCollection", features };
}

function addAnalysisLayers(map) {
  const sources = ["excluded", "buildable", "constraints", "parcel", "manual", "draft"];
  sources.forEach((id) => map.addSource(id, { type: "geojson", data: EMPTY_COLLECTION }));
  map.addLayer({ id: "excluded-fill", type: "fill", source: "excluded", paint: { "fill-color": "#e85d45", "fill-opacity": 0.48 } });
  map.addLayer({ id: "buildable-fill", type: "fill", source: "buildable", paint: { "fill-color": "#2d9c69", "fill-opacity": 0.62 } });
  map.addLayer({ id: "constraint-fill", type: "fill", source: "constraints", paint: { "fill-color": "#805ad5", "fill-opacity": 0.2, "fill-outline-color": "#6941c6" } });
  map.addLayer({ id: "manual-fill", type: "fill", source: "manual", paint: { "fill-color": ["match", ["get", "kind"], "restore", "#16a56a", "#c83e4d"], "fill-opacity": 0.28 } });
  map.addLayer({ id: "manual-line", type: "line", source: "manual", paint: { "line-color": ["match", ["get", "kind"], "restore", "#087443", "#932432"], "line-width": 2, "line-dasharray": [2, 2] } });
  map.addLayer({ id: "parcel-line", type: "line", source: "parcel", paint: { "line-color": "#17211b", "line-width": 2.5 } });
  map.addLayer({ id: "draft-line", type: "line", source: "draft", filter: ["==", "$type", "LineString"], paint: { "line-color": "#17211b", "line-width": 2.5, "line-dasharray": [2, 1] } });
  map.addLayer({ id: "draft-points", type: "circle", source: "draft", filter: ["==", "$type", "Point"], paint: { "circle-radius": 5, "circle-color": "#ffffff", "circle-stroke-color": "#17211b", "circle-stroke-width": 2 } });
}

function MapView({ parcel, result, mode, setDraftPoints, draftPoints, manualEdits }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const modeRef = useRef(mode);
  const fittedParcelRef = useRef(null);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => { modeRef.current = mode; }, [mode]);

  useEffect(() => {
    const map = new maplibregl.Map({ container: containerRef.current, style: BASE_STYLE, center: [-97.7342, 30.2755], zoom: 14 });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.on("load", () => {
      addAnalysisLayers(map);
      setMapReady(true);
    });
    map.on("click", (event) => {
      if (modeRef.current) setDraftPoints((points) => [...points, event.lngLat]);
    });
    map.on("click", "constraint-fill", (event) => {
      if (modeRef.current || !event.features?.[0]) return;
      const properties = event.features[0].properties;
      const content = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = properties.label;
      const detail = document.createElement("p");
      detail.textContent = `${properties.reason} Setback: ${properties.setback_m} m.`;
      content.append(title, detail);
      new maplibregl.Popup({ closeButton: true }).setLngLat(event.lngLat).setDOMContent(content).addTo(map);
    });
    map.on("mouseenter", "constraint-fill", () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", "constraint-fill", () => { map.getCanvas().style.cursor = modeRef.current ? "crosshair" : ""; });
    mapRef.current = map;
    return () => map.remove();
  }, [setDraftPoints]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.loaded()) return;
    map.getCanvas().style.cursor = mode ? "crosshair" : "";
  }, [mode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || !result || !map.getSource("parcel")) return;
    map.getSource("parcel").setData(asCollection(result.features.parcel));
    map.getSource("buildable").setData(asCollection(result.features.buildable));
    map.getSource("excluded").setData(asCollection(result.features.excluded));
    map.getSource("constraints").setData(result.features.constraints);
    map.getSource("draft").setData(draftGeoJSON(draftPoints));
    map.getSource("manual").setData({
      type: "FeatureCollection",
      features: manualEdits.map((edit) => ({ type: "Feature", properties: { kind: edit.kind }, geometry: edit.geometry })),
    });
    const parcelId = parcel?.properties?.id;
    if (parcelId && fittedParcelRef.current !== parcelId) {
      const bounds = boundsFor(parcel);
      if (bounds) map.fitBounds(bounds, { padding: 56, duration: 500 });
      fittedParcelRef.current = parcelId;
    }
  }, [parcel, result, draftPoints, manualEdits, mapReady]);

  return <div ref={containerRef} className="map" aria-label="Buildable area map" />;
}

function App() {
  const [parcels, setParcels] = useState([]);
  const [parcelQuery, setParcelQuery] = useState("");
  const [parcelTotal, setParcelTotal] = useState(0);
  const [parcel, setParcel] = useState(null);
  const [layers, setLayers] = useState([]);
  const [policyProfiles, setPolicyProfiles] = useState([]);
  const [policyProfile, setPolicyProfile] = useState("screening");
  const [customizedPolicy, setCustomizedPolicy] = useState(false);
  const [result, setResult] = useState(null);
  const [manualEdits, setManualEdits] = useState([]);
  const [mode, setMode] = useState(null);
  const [draftPoints, setDraftPoints] = useState([]);
  const [status, setStatus] = useState("Loading analysis data…");

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/layers`).then((response) => response.json()),
      fetch(`${API_BASE}/api/parcels/search`).then((response) => response.json()),
    ]).then(async ([layerData, parcelData]) => {
      const selectedProfile = layerData.profiles.find((profile) => profile.id === layerData.default_profile);
      const configured = layerData.layers.map((layer) => ({
        ...layer,
        enabled: true,
        setback_m: selectedProfile?.setbacks_m[layer.id] ?? layer.default_setback_m,
      }));
      setLayers(configured);
      setPolicyProfiles(layerData.profiles);
      setPolicyProfile(layerData.default_profile);
      setParcels(parcelData.parcels);
      setParcelTotal(parcelData.total ?? parcelData.parcels.length);
      const initialParcelId = parcelData.featured_parcel_id ?? parcelData.parcels[0]?.id;
      if (initialParcelId) {
        const feature = await fetch(`${API_BASE}/api/parcels/${initialParcelId}`).then((response) => response.json());
        setParcel(feature);
      }
    }).catch(() => setStatus("Could not connect to the analysis API."));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      fetch(`${API_BASE}/api/parcels/search?q=${encodeURIComponent(parcelQuery)}&limit=100`, { signal: controller.signal })
        .then((response) => response.json())
        .then((data) => {
          setParcels(data.parcels);
          setParcelTotal(data.total);
        })
        .catch((error) => {
          if (error.name !== "AbortError") setStatus("Parcel search failed.");
        });
    }, 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [parcelQuery]);

  const requestBody = useMemo(() => parcel ? {
    parcel_id: parcel.properties.id,
    policy_profile: policyProfile,
    layers: layers.map(({ id, enabled, setback_m }) => ({ id, enabled, setback_m })),
    manual_edits: manualEdits,
  } : null, [parcel, policyProfile, layers, manualEdits]);

  useEffect(() => {
    if (!requestBody || !layers.length) return undefined;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setStatus("Analyzing…");
      fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
        signal: controller.signal,
      }).then(async (response) => {
        if (!response.ok) throw new Error((await response.json()).detail ?? "Analysis failed");
        return response.json();
      }).then((data) => {
        setResult(data);
        setStatus("Current");
      }).catch((error) => {
        if (error.name !== "AbortError") setStatus(error.message);
      });
    }, 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [requestBody, layers.length]);

  const chooseParcel = async (id) => {
    setStatus("Loading parcel…");
    const feature = await fetch(`${API_BASE}/api/parcels/${id}`).then((response) => response.json());
    setParcel(feature);
    setManualEdits([]);
  };

  const finishPolygon = () => {
    if (!mode || draftPoints.length < 3) return;
    const kind = mode === "exclude" ? "carve-out" : "restore";
    setManualEdits((edits) => [...edits, {
      id: crypto.randomUUID(),
      label: `${kind === "carve-out" ? "Carve-out" : "Restore"} ${edits.filter((edit) => edit.kind === kind).length + 1}`,
      kind,
      geometry: polygonFrom(draftPoints),
    }]);
    setDraftPoints([]);
    setMode(null);
  };

  const updateLayer = (id, changes) => {
    setCustomizedPolicy(true);
    setLayers((items) => items.map((item) => item.id === id ? { ...item, ...changes } : item));
  };

  const choosePolicyProfile = (profileId) => {
    const profile = policyProfiles.find((item) => item.id === profileId);
    setPolicyProfile(profileId);
    setCustomizedPolicy(false);
    setLayers((items) => items.map((item) => ({ ...item, enabled: true, setback_m: profile.setbacks_m[item.id] })));
  };

  return (
    <main className="shell">
      <aside className="sidebar">
        <header className="brand">
          <div><span>Site intelligence</span><h1>Buildable area</h1></div>
          <strong>{result ? `${result.buildable_acres.toFixed(2)} ac` : "—"}</strong>
        </header>

        <label className="parcel-select">Find parcel
          <input value={parcelQuery} onChange={(event) => setParcelQuery(event.target.value)} placeholder="Address or parcel ID" />
          <small>{parcelTotal.toLocaleString()} matching parcels</small>
        </label>
        <label className="parcel-select">Parcel
          <select value={parcel?.properties?.id ?? ""} onChange={(event) => chooseParcel(event.target.value)}>
            {parcel && !parcels.some((item) => item.id === parcel.properties.id) && <option value={parcel.properties.id}>{parcel.properties.name} · {parcel.properties.id}</option>}
            {parcels.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.id}</option>)}
          </select>
        </label>

        {result && <section className="metrics" aria-label="Analysis totals">
          <div><span>Parcel</span><strong>{result.parcel_acres.toFixed(2)} ac</strong></div>
          <div><span>Excluded</span><strong>{result.excluded_acres.toFixed(2)} ac</strong></div>
          <div><span>Buildable</span><strong>{result.buildable_acres.toFixed(2)} ac</strong></div>
        </section>}

        <section>
          <div className="section-title"><h2>Constraint layers</h2><span className={status === "Current" ? "status current" : "status"}>{status}</span></div>
          <label className="policy-select">Policy profile
            <select value={policyProfile} onChange={(event) => choosePolicyProfile(event.target.value)}>
              {policyProfiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.label}</option>)}
            </select>
            <small>{customizedPolicy ? "Custom overrides applied" : policyProfiles.find((profile) => profile.id === policyProfile)?.description}</small>
          </label>
          <div className="setbacks">
            {layers.map((layer) => <div className={layer.enabled ? "layer-card" : "layer-card disabled"} key={layer.id}>
              <label className="layer-toggle"><input type="checkbox" checked={layer.enabled} onChange={(event) => updateLayer(layer.id, { enabled: event.target.checked })} /><span><strong>{layer.label}</strong><small>{layer.source}</small></span></label>
              <label className="setback-input">Setback <input type="number" min={layer.min_setback_m} max={layer.max_setback_m} step={layer.step_m} disabled={!layer.enabled} value={layer.setback_m} onChange={(event) => updateLayer(layer.id, { setback_m: Number(event.target.value) })} /><span>m</span></label>
              <small className="layer-basis">{layer.geometry_basis}</small>
            </div>)}
          </div>
        </section>

        <section>
          <h2>Manual review</h2>
          <div className="toolbar">
            <button className={mode === "exclude" ? "active danger" : "danger"} onClick={() => { setMode("exclude"); setDraftPoints([]); }}><Minus size={16} /> Carve out</button>
            <button className={mode === "restore" ? "active success" : "success"} onClick={() => { setMode("restore"); setDraftPoints([]); }}><Plus size={16} /> Restore</button>
            <button onClick={finishPolygon} disabled={draftPoints.length < 3}><Check size={16} /> Finish</button>
            <button className="icon-button" onClick={() => setDraftPoints([])} disabled={!draftPoints.length} aria-label="Clear sketch"><RotateCcw size={16} /></button>
          </div>
          {mode && <p className="hint">Click at least three map points, then finish the polygon.</p>}
          <div className="edit-list">
            {manualEdits.map((edit) => <div key={edit.id}><span className={edit.kind}>{edit.label}</span><button onClick={() => setManualEdits((items) => items.filter((item) => item.id !== edit.id))} aria-label={`Remove ${edit.label}`}><X size={15} /></button></div>)}
            {!!manualEdits.length && <button className="clear-edits" onClick={() => setManualEdits([])}><Trash2 size={14} /> Clear all edits</button>}
          </div>
        </section>

        <section>
          <h2>Attribution</h2>
          <div className="breakdown">
            {result?.breakdown.map((row) => <div className="breakdown-row" key={row.id}>
              <div><strong>{row.label}</strong><span>{row.removed_acres < 0 ? "Restored" : "Exclusively removed"} · {row.overlap_acres.toFixed(2)} ac overlap</span></div>
              <b>{row.removed_acres.toFixed(2)} ac</b>
            </div>)}
          </div>
          {result && <p className="method">{result.area_method} ({result.analysis_crs}). Overlap diagnostics: {result.overlap_diagnostics.duplicate_overlap_acres.toFixed(2)} ac duplicated across layers.</p>}
        </section>
        <p className="disclaimer">Planning estimate only — not a survey, title opinion, or legal determination.</p>
      </aside>

      <section className="map-panel">
        <MapView parcel={parcel} result={result} mode={mode} setDraftPoints={setDraftPoints} draftPoints={draftPoints} manualEdits={manualEdits} />
        <div className="legend"><span><i className="buildable" />Buildable</span><span><i className="excluded" />Excluded</span><span><i className="constraint" />Constraint extent</span></div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
