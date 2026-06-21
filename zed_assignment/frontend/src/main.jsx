import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import maplibregl from "maplibre-gl";
import {
  Check,
  ChevronDown,
  ChevronUp,
  CircleHelp,
  Copy,
  Download,
  Focus,
  Info,
  Minus,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Redo2,
  RotateCcw,
  Trash2,
  Undo2,
  X,
} from "lucide-react";
import "maplibre-gl/dist/maplibre-gl.css";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const EMPTY_COLLECTION = { type: "FeatureCollection", features: [] };
const LAYER_COLORS = {
  wetlands: "#326f68",
  floodplain: "#3978a8",
  transmission: "#c17b26",
  "manual-exclusions": "#b94752",
  "manual-restores": "#25845a",
};

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

function colorExpression() {
  return [
    "match",
    ["get", "id"],
    "wetlands", LAYER_COLORS.wetlands,
    "floodplain", LAYER_COLORS.floodplain,
    "transmission", LAYER_COLORS.transmission,
    "#69756d",
  ];
}

function addAnalysisLayers(map) {
  ["ghost", "excluded", "buildable", "constraints", "parcel", "manual", "draft"].forEach((id) => {
    map.addSource(id, { type: "geojson", data: EMPTY_COLLECTION });
  });
  map.addLayer({ id: "excluded-fill", type: "fill", source: "excluded", paint: { "fill-color": "#b94752", "fill-opacity": 0.2 } });
  map.addLayer({ id: "buildable-fill", type: "fill", source: "buildable", paint: { "fill-color": "#2d8a5d", "fill-opacity": 0.58 } });
  map.addLayer({ id: "ghost-line", type: "line", source: "ghost", paint: { "line-color": "#ffffff", "line-opacity": 0.8, "line-width": 3, "line-dasharray": [1.5, 1.5] } });
  map.addLayer({ id: "constraint-fill", type: "fill", source: "constraints", paint: { "fill-color": colorExpression(), "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.66, 0.42] } });
  map.addLayer({ id: "constraint-line", type: "line", source: "constraints", paint: { "line-color": colorExpression(), "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 3, 1.5] } });
  map.addLayer({ id: "manual-fill", type: "fill", source: "manual", paint: { "fill-color": ["match", ["get", "kind"], "restore", LAYER_COLORS["manual-restores"], LAYER_COLORS["manual-exclusions"]], "fill-opacity": ["case", ["boolean", ["get", "pending"], false], 0.18, 0.3] } });
  map.addLayer({ id: "manual-line", type: "line", source: "manual", paint: { "line-color": ["match", ["get", "kind"], "restore", "#176d47", "#912f3a"], "line-width": 2, "line-dasharray": [2, 2] } });
  map.addLayer({ id: "parcel-line", type: "line", source: "parcel", paint: { "line-color": "#152019", "line-width": 2.5 } });
  map.addLayer({ id: "draft-line", type: "line", source: "draft", filter: ["==", "$type", "LineString"], paint: { "line-color": "#152019", "line-width": 2.5, "line-dasharray": [2, 1] } });
  map.addLayer({ id: "draft-points", type: "circle", source: "draft", filter: ["==", "$type", "Point"], paint: { "circle-radius": 5, "circle-color": "#ffffff", "circle-stroke-color": "#152019", "circle-stroke-width": 2 } });
}

function polygonRings(feature) {
  const geometry = feature?.geometry;
  if (!geometry) return [];
  if (geometry.type === "Polygon") return geometry.coordinates;
  if (geometry.type === "MultiPolygon") return geometry.coordinates.flat();
  return [];
}

function snappedPoint(map, lngLat, parcel, threshold = 14) {
  const cursor = map.project(lngLat);
  let nearest = null;
  polygonRings(parcel).forEach((ring) => {
    for (let index = 1; index < ring.length; index += 1) {
      const start = map.project(ring[index - 1]);
      const end = map.project(ring[index]);
      const dx = end.x - start.x;
      const dy = end.y - start.y;
      const lengthSquared = dx * dx + dy * dy || 1;
      const ratio = Math.max(0, Math.min(1, ((cursor.x - start.x) * dx + (cursor.y - start.y) * dy) / lengthSquared));
      const x = start.x + ratio * dx;
      const y = start.y + ratio * dy;
      const distance = Math.hypot(cursor.x - x, cursor.y - y);
      if (!nearest || distance < nearest.distance) nearest = { distance, point: map.unproject([x, y]) };
    }
  });
  return nearest?.distance <= threshold ? nearest.point : lngLat;
}

class MapErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return <div className="map-fallback" role="alert"><strong>Map unavailable</strong><span>This browser could not start WebGL. The analysis controls and totals remain available.</span></div>;
    }
    return this.props.children;
  }
}

function MapView({ parcel, result, ghostBuildable, mode, setDraftPoints, draftPoints, manualEdits, pending, onExportReady }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const modeRef = useRef(mode);
  const parcelRef = useRef(parcel);
  const fittedParcelRef = useRef(null);
  const popupRef = useRef(null);
  const hoveredIdRef = useRef(null);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => { modeRef.current = mode; }, [mode]);
  useEffect(() => { parcelRef.current = parcel; }, [parcel]);

  useEffect(() => {
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center: [-97.7342, 30.2755],
      zoom: 14,
      preserveDrawingBuffer: true,
      cooperativeGestures: false,
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.on("load", () => {
      addAnalysisLayers(map);
      setMapReady(true);
      onExportReady({
        snapshot: () => map.getCanvas().toDataURL("image/png"),
        focus: () => {
          const bounds = boundsFor(parcelRef.current);
          if (bounds) map.fitBounds(bounds, { padding: 56, duration: 450 });
        },
      });
    });
    map.on("click", (event) => {
      if (!modeRef.current) return;
      const point = modeRef.current === "restore" ? snappedPoint(map, event.lngLat, parcelRef.current) : event.lngLat;
      setDraftPoints((points) => [...points, point]);
    });
    map.on("mousemove", "constraint-fill", (event) => {
      if (modeRef.current || !event.features?.[0]) return;
      const feature = event.features[0];
      if (hoveredIdRef.current !== null) map.setFeatureState({ source: "constraints", id: hoveredIdRef.current }, { hover: false });
      hoveredIdRef.current = feature.id;
      if (feature.id !== undefined) map.setFeatureState({ source: "constraints", id: feature.id }, { hover: true });
      const properties = feature.properties;
      const content = document.createElement("div");
      content.className = "map-tooltip";
      const title = document.createElement("strong");
      title.textContent = properties.label;
      const detail = document.createElement("span");
      detail.textContent = `${Number(properties.setback_m).toFixed(1)} m setback`;
      content.append(title, detail);
      if (!popupRef.current) popupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 12 });
      popupRef.current.setLngLat(event.lngLat).setDOMContent(content).addTo(map);
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "constraint-fill", () => {
      if (hoveredIdRef.current !== null) map.setFeatureState({ source: "constraints", id: hoveredIdRef.current }, { hover: false });
      hoveredIdRef.current = null;
      popupRef.current?.remove();
      map.getCanvas().style.cursor = modeRef.current ? "crosshair" : "";
    });
    mapRef.current = map;
    return () => map.remove();
  }, [onExportReady, setDraftPoints]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.loaded()) return;
    map.getCanvas().style.cursor = mode ? "crosshair" : "";
  }, [mode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || !result || !map.getSource("parcel")) return;
    const constraints = {
      ...result.features.constraints,
      features: result.features.constraints.features.map((feature, index) => ({ ...feature, id: feature.properties.id ?? index })),
    };
    map.getSource("parcel").setData(asCollection(result.features.parcel));
    map.getSource("buildable").setData(asCollection(result.features.buildable));
    map.getSource("ghost").setData(asCollection(ghostBuildable));
    map.getSource("excluded").setData(asCollection(result.features.excluded));
    map.getSource("constraints").setData(constraints);
    map.getSource("draft").setData(draftGeoJSON(draftPoints));
    map.getSource("manual").setData({
      type: "FeatureCollection",
      features: manualEdits.map((edit) => ({ type: "Feature", properties: { kind: edit.kind, pending }, geometry: edit.geometry })),
    });
    const parcelId = parcel?.properties?.id;
    if (parcelId && fittedParcelRef.current !== parcelId) {
      const bounds = boundsFor(parcel);
      if (bounds) map.fitBounds(bounds, { padding: 56, duration: 500 });
      fittedParcelRef.current = parcelId;
    }
  }, [parcel, result, ghostBuildable, draftPoints, manualEdits, pending, mapReady]);

  return <div ref={containerRef} className="map" role="application" aria-label="Interactive buildable area map" />;
}

function useEditHistory() {
  const [history, setHistory] = useState({ past: [], present: [], future: [] });
  const commit = useCallback((nextOrUpdater) => {
    setHistory((current) => {
      const next = typeof nextOrUpdater === "function" ? nextOrUpdater(current.present) : nextOrUpdater;
      return { past: [...current.past, current.present], present: next, future: [] };
    });
  }, []);
  const undo = useCallback(() => setHistory((current) => {
    if (!current.past.length) return current;
    const previous = current.past.at(-1);
    return { past: current.past.slice(0, -1), present: previous, future: [current.present, ...current.future] };
  }), []);
  const redo = useCallback(() => setHistory((current) => {
    if (!current.future.length) return current;
    const next = current.future[0];
    return { past: [...current.past, current.present], present: next, future: current.future.slice(1) };
  }), []);
  const reset = useCallback((value = []) => setHistory({ past: [], present: value, future: [] }), []);
  return { edits: history.present, canUndo: Boolean(history.past.length), canRedo: Boolean(history.future.length), commit, undo, redo, reset };
}

function unitValue(acres, unit) {
  if (unit === "sqft") return acres * 43560;
  if (unit === "ha") return acres * 0.40468564224;
  return acres;
}

function formatArea(acres, unit, compact = false) {
  const value = unitValue(acres, unit);
  const labels = { acres: "ac", sqft: "sq ft", ha: "ha" };
  const maximumFractionDigits = unit === "sqft" ? 0 : compact ? 1 : 2;
  const minimumFractionDigits = unit === "sqft" ? 0 : compact ? 1 : 2;
  return `${value.toLocaleString(undefined, { maximumFractionDigits, minimumFractionDigits })} ${labels[unit]}`;
}

function encodeScenario(value) {
  return window.btoa(unescape(encodeURIComponent(JSON.stringify(value))));
}

function decodeScenario(value) {
  try {
    return JSON.parse(decodeURIComponent(escape(window.atob(value))));
  } catch {
    return null;
  }
}

function Walkthrough({ step, onNext, onClose }) {
  const steps = [
    ["1 of 3", "Start with a parcel", "The demo parcel is already selected. Search by address or parcel ID whenever you want to switch."],
    ["2 of 3", "Test policy assumptions", "Turn constraints on or off and drag setbacks. The map keeps the previous boundary visible while it updates."],
    ["3 of 3", "Fine-tune the result", "Carve out or restore an area on the map, then undo, redo, share, or export the scenario."],
  ];
  const [counter, title, body] = steps[step];
  return <div className={`tour tour-${step + 1}`} role="dialog" aria-modal="false" aria-labelledby="tour-title">
    <button className="tour-close" onClick={onClose} aria-label="Dismiss walkthrough"><X size={16} /></button>
    <span>{counter}</span><h2 id="tour-title">{title}</h2><p>{body}</p>
    <button className="primary-button" onClick={step === 2 ? onClose : onNext}>{step === 2 ? "Start exploring" : "Next"}</button>
  </div>;
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
  const [ghostBuildable, setGhostBuildable] = useState(null);
  const { edits: manualEdits, canUndo, canRedo, commit: commitEdits, undo, redo, reset: resetEdits } = useEditHistory();
  const [mode, setMode] = useState(null);
  const [draftPoints, setDraftPoints] = useState([]);
  const [status, setStatus] = useState("Loading analysis data…");
  const [pending, setPending] = useState(false);
  const [units, setUnits] = useState("acres");
  const [panelOpen, setPanelOpen] = useState(true);
  const [detailsOpen, setDetailsOpen] = useState(true);
  const [copied, setCopied] = useState(false);
  const [tourStep, setTourStep] = useState(() => window.localStorage.getItem("buildable-tour-seen") ? null : 0);
  const mapActionsRef = useRef({ download: () => {}, focus: () => {} });
  const ghostTimerRef = useRef(null);
  const requestedScenarioRef = useRef(decodeScenario(new URLSearchParams(window.location.search).get("scenario")));
  const setMapActions = useCallback((actions) => { mapActionsRef.current = actions; }, []);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/layers`).then((response) => response.json()),
      fetch(`${API_BASE}/api/parcels/search`).then((response) => response.json()),
    ]).then(async ([layerData, parcelData]) => {
      const shared = requestedScenarioRef.current;
      const profileId = shared?.profile && layerData.profiles.some((profile) => profile.id === shared.profile) ? shared.profile : layerData.default_profile;
      const selectedProfile = layerData.profiles.find((profile) => profile.id === profileId);
      const sharedSetbacks = Object.fromEntries(shared?.layers?.map((layer) => [layer.id, layer]) ?? []);
      const configured = layerData.layers.map((layer) => ({
        ...layer,
        enabled: sharedSetbacks[layer.id]?.enabled ?? true,
        setback_m: sharedSetbacks[layer.id]?.setback_m ?? selectedProfile?.setbacks_m[layer.id] ?? layer.default_setback_m,
      }));
      setLayers(configured);
      setPolicyProfiles(layerData.profiles);
      setPolicyProfile(profileId);
      setUnits(shared?.units ?? "acres");
      if (shared?.edits) resetEdits(shared.edits);
      setParcels(parcelData.parcels);
      setParcelTotal(parcelData.total ?? parcelData.parcels.length);
      const initialParcelId = shared?.parcelId ?? parcelData.featured_parcel_id ?? parcelData.parcels[0]?.id;
      if (initialParcelId) {
        const feature = await fetch(`${API_BASE}/api/parcels/${initialParcelId}`).then((response) => response.json());
        setParcel(feature);
      }
    }).catch(() => setStatus("Could not connect to the analysis API."));
  }, [resetEdits]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      fetch(`${API_BASE}/api/parcels/search?q=${encodeURIComponent(parcelQuery)}&limit=100`, { signal: controller.signal })
        .then((response) => response.json())
        .then((data) => { setParcels(data.parcels); setParcelTotal(data.total); })
        .catch((error) => { if (error.name !== "AbortError") setStatus("Parcel search failed."); });
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
    setPending(true);
    setStatus("Updating…");
    const timer = window.setTimeout(() => {
      setGhostBuildable(result?.features?.buildable ?? null);
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
        setPending(false);
        setStatus("Current");
        window.clearTimeout(ghostTimerRef.current);
        ghostTimerRef.current = window.setTimeout(() => setGhostBuildable(null), 1100);
      }).catch((error) => {
        if (error.name !== "AbortError") { setPending(false); setStatus(error.message); }
      });
    }, 350);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [requestBody, layers.length]);

  useEffect(() => () => window.clearTimeout(ghostTimerRef.current), []);

  useEffect(() => {
    const handleKeyDown = (event) => {
      const typing = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName);
      if (event.key === "Escape") { setDraftPoints([]); setMode(null); }
      if (!typing && event.key === "Enter" && mode && draftPoints.length >= 3) finishPolygon();
      if (!typing && (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (event.shiftKey) redo(); else undo();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const chooseParcel = async (id) => {
    setStatus("Loading parcel…");
    const feature = await fetch(`${API_BASE}/api/parcels/${id}`).then((response) => response.json());
    setParcel(feature);
    resetEdits();
    setDraftPoints([]);
  };

  const finishPolygon = () => {
    if (!mode || draftPoints.length < 3) return;
    const kind = mode === "exclude" ? "carve-out" : "restore";
    commitEdits((edits) => [...edits, {
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

  const closeTour = () => {
    window.localStorage.setItem("buildable-tour-seen", "true");
    setTourStep(null);
  };

  const shareScenario = async () => {
    const scenario = {
      parcelId: parcel?.properties?.id,
      profile: policyProfile,
      units,
      layers: layers.map(({ id, enabled, setback_m }) => ({ id, enabled, setback_m })),
      edits: manualEdits,
    };
    const url = new URL(window.location.href);
    url.searchParams.set("scenario", encodeScenario(scenario));
    window.history.replaceState({}, "", url);
    try {
      await navigator.clipboard.writeText(url.toString());
    } catch {
      const field = document.createElement("textarea");
      field.value = url.toString();
      field.style.position = "fixed";
      field.style.opacity = "0";
      document.body.append(field);
      field.select();
      document.execCommand("copy");
      field.remove();
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  const exportScenario = async () => {
    if (!result) return;
    const canvas = document.createElement("canvas");
    canvas.width = 1400;
    canvas.height = 900;
    const context = canvas.getContext("2d");
    context.fillStyle = "#f8faf7";
    context.fillRect(0, 0, canvas.width, canvas.height);
    try {
      const image = new Image();
      image.src = mapActionsRef.current.snapshot();
      await image.decode();
      context.drawImage(image, 0, 0, 980, 900);
    } catch {
      context.fillStyle = "#e9ede8";
      context.fillRect(0, 0, 980, 900);
      context.fillStyle = "#667169";
      context.font = "24px sans-serif";
      context.fillText("Map image unavailable", 340, 450);
    }
    context.fillStyle = "#ffffff";
    context.fillRect(980, 0, 420, 900);
    context.fillStyle = "#17211b";
    context.font = "500 35px Georgia, serif";
    context.fillText("Buildable area", 1020, 72);
    context.fillStyle = "#667169";
    context.font = "16px sans-serif";
    context.fillText(parcel?.properties?.name ?? parcel?.properties?.id ?? "Selected parcel", 1020, 106, 340);
    context.fillStyle = "#174c35";
    context.fillRect(1020, 140, 340, 78);
    context.fillStyle = "#ffffff";
    context.font = "700 32px sans-serif";
    context.fillText(formatArea(result.buildable_acres, units), 1042, 188);
    context.fillStyle = "#17211b";
    context.font = "700 14px sans-serif";
    context.fillText("LAND BALANCE", 1020, 270);
    context.font = "16px sans-serif";
    context.fillText(`Parcel: ${formatArea(result.parcel_acres, units)}`, 1020, 308);
    context.fillText(`Excluded: ${formatArea(result.excluded_acres, units)}`, 1020, 340);
    context.fillText(`Buildable: ${formatArea(result.buildable_acres, units)}`, 1020, 372);
    context.font = "700 14px sans-serif";
    context.fillText("ATTRIBUTION", 1020, 430);
    let y = 468;
    result.breakdown.forEach((row) => {
      context.fillStyle = LAYER_COLORS[row.id] ?? "#69756d";
      context.fillRect(1020, y - 11, 10, 10);
      context.fillStyle = "#17211b";
      context.font = "600 14px sans-serif";
      context.fillText(row.label, 1042, y, 205);
      context.textAlign = "right";
      context.fillText(formatArea(row.removed_acres, units), 1360, y);
      context.textAlign = "left";
      y += 38;
    });
    context.fillStyle = "#667169";
    context.font = "13px sans-serif";
    context.fillText("Overlapping exclusions are counted once.", 1020, 795);
    context.fillText("Planning estimate only. Not a legal determination.", 1020, 824);
    const link = document.createElement("a");
    link.download = `buildable-area-${parcel?.properties?.id ?? "scenario"}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  };

  const totalWidth = result?.parcel_acres || 1;
  const buildableWidth = Math.max(0, Math.min(100, ((result?.buildable_acres ?? 0) / totalWidth) * 100));

  return (
    <main className={`shell ${panelOpen ? "" : "panel-collapsed"}`}>
      <aside className="sidebar" aria-label="Analysis controls">
        <header className="brand">
          <div><span>Site intelligence</span><h1>Buildable area</h1></div>
          <div className="headline-total"><strong>{result ? formatArea(result.buildable_acres, units, true) : "—"}</strong>{pending && <i className="spinner" aria-label="Updating analysis" />}</div>
        </header>

        <div className="scenario-actions" aria-label="Scenario actions">
          <button onClick={shareScenario} disabled={!result} title="Copy a link to this scenario"><Copy size={15} /> {copied ? "Link copied" : "Share"}</button>
          <button onClick={exportScenario} disabled={!result} title="Download map and attribution as an image"><Download size={15} /> Export</button>
          <button className="icon-button" onClick={() => mapActionsRef.current.focus()} disabled={!parcel} title="Fit map to parcel" aria-label="Fit map to parcel"><Focus size={16} /></button>
          <button className="icon-button" onClick={() => setTourStep(0)} title="Open walkthrough" aria-label="Open walkthrough"><CircleHelp size={16} /></button>
        </div>

        <section className="parcel-controls">
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
        </section>

        {result && <section className="summary" aria-label="Analysis totals">
          <div className="summary-heading"><h2>Land balance</h2><div className="unit-toggle" aria-label="Area units">
            {[['acres', 'Ac'], ['sqft', 'Ft²'], ['ha', 'Ha']].map(([id, label]) => <button key={id} className={units === id ? "active" : ""} onClick={() => setUnits(id)}>{label}</button>)}
          </div></div>
          <div className="metrics">
            <div><span>Parcel</span><strong>{formatArea(result.parcel_acres, units)}</strong></div>
            <div><span>Excluded</span><strong>{formatArea(result.excluded_acres, units)}</strong></div>
            <div><span>Buildable</span><strong>{formatArea(result.buildable_acres, units)}</strong></div>
          </div>
          <div className="balance-bar" role="img" aria-label={`${buildableWidth.toFixed(0)} percent buildable`}>
            <i className="bar-buildable" style={{ width: `${buildableWidth}%` }} /><i className="bar-excluded" style={{ width: `${100 - buildableWidth}%` }} />
          </div>
          <div className="balance-labels"><span><i className="buildable-swatch" />{buildableWidth.toFixed(0)}% buildable</span><span><i className="excluded-swatch" />{(100 - buildableWidth).toFixed(0)}% excluded</span></div>
        </section>}

        <section>
          <div className="section-title"><h2>Constraint layers</h2><span className={status === "Current" ? "status current" : "status"}>{pending && <i className="spinner" />}{status}</span></div>
          <label className="policy-select">Policy profile
            <select value={policyProfile} onChange={(event) => choosePolicyProfile(event.target.value)}>
              {policyProfiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.label}</option>)}
            </select>
            <small>{customizedPolicy ? "Custom overrides applied" : policyProfiles.find((profile) => profile.id === policyProfile)?.description}</small>
          </label>
          <div className="setbacks">
            {layers.map((layer) => <div className={layer.enabled ? "layer-row" : "layer-row disabled"} key={layer.id}>
              <label className="layer-toggle"><input type="checkbox" checked={layer.enabled} onChange={(event) => updateLayer(layer.id, { enabled: event.target.checked })} /><i style={{ background: LAYER_COLORS[layer.id] }} /><span><strong>{layer.label}</strong><small>{layer.source}</small></span></label>
              <label className="setback-control"><span>Setback</span><input type="range" min={layer.min_setback_m} max={layer.max_setback_m} step={layer.step_m} disabled={!layer.enabled} value={layer.setback_m} onChange={(event) => updateLayer(layer.id, { setback_m: Number(event.target.value) })} /><input aria-label={`${layer.label} setback in metres`} type="number" min={layer.min_setback_m} max={layer.max_setback_m} step={layer.step_m} disabled={!layer.enabled} value={layer.setback_m} onChange={(event) => updateLayer(layer.id, { setback_m: Number(event.target.value) })} /><b>m</b></label>
              <small className="layer-basis">{layer.geometry_basis}</small>
            </div>)}
          </div>
        </section>

        <section>
          <div className="section-title"><h2>Manual review</h2><div className="history-actions">
            <button onClick={undo} disabled={!canUndo} title="Undo (Ctrl/⌘ Z)" aria-label="Undo"><Undo2 size={15} /></button>
            <button onClick={redo} disabled={!canRedo} title="Redo (Ctrl/⌘ Shift Z)" aria-label="Redo"><Redo2 size={15} /></button>
          </div></div>
          <div className="toolbar">
            <button className={mode === "exclude" ? "active danger" : "danger"} onClick={() => { setMode("exclude"); setDraftPoints([]); }}><Minus size={16} /> Carve out</button>
            <button className={mode === "restore" ? "active success" : "success"} onClick={() => { setMode("restore"); setDraftPoints([]); }}><Plus size={16} /> Restore</button>
            <button onClick={finishPolygon} disabled={draftPoints.length < 3}><Check size={16} /> Finish</button>
            <button className="icon-button" onClick={() => setDraftPoints([])} disabled={!draftPoints.length} title="Clear sketch" aria-label="Clear sketch"><RotateCcw size={16} /></button>
          </div>
          {mode && <p className="hint">{mode === "restore" ? "Restore points snap to the parcel edge. " : ""}Add 3+ points, then finish. Esc cancels.</p>}
          <div className="edit-list">
            {manualEdits.map((edit) => <div className={pending ? "pending" : ""} key={edit.id}><span className={edit.kind}>{edit.label}</span><button onClick={() => commitEdits((items) => items.filter((item) => item.id !== edit.id))} aria-label={`Remove ${edit.label}`}><X size={15} /></button></div>)}
            {!!manualEdits.length && <button className="clear-edits" onClick={() => commitEdits([])}><Trash2 size={14} /> Clear all edits</button>}
          </div>
        </section>

        <section>
          <button className="breakdown-toggle" onClick={() => setDetailsOpen((open) => !open)} aria-expanded={detailsOpen}><span>Attribution</span>{detailsOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</button>
          {detailsOpen && <>
            <div className="overlap-note"><Info size={14} /><span>Overlapping excluded areas are counted once in totals.</span></div>
            <div className="breakdown">
              {result?.breakdown.map((row) => <div className="breakdown-row" key={row.id}>
                <i style={{ background: LAYER_COLORS[row.id] ?? "#69756d" }} />
                <div><strong>{row.label}</strong><span>{row.removed_acres < 0 ? "Restored" : "Exclusively removed"} · {formatArea(row.overlap_acres, units)} overlap</span></div>
                <b>{formatArea(row.removed_acres, units)}</b>
              </div>)}
            </div>
            {result && <p className="method">{result.area_method} ({result.analysis_crs}). Duplicate layer overlap: {formatArea(result.overlap_diagnostics.duplicate_overlap_acres, units)}.</p>}
          </>}
        </section>
        <p className="disclaimer">Planning estimate only. Not a survey, title opinion, or legal determination.</p>
      </aside>

      <section className="map-panel" aria-label="Map workspace">
        <MapErrorBoundary><MapView parcel={parcel} result={result} ghostBuildable={ghostBuildable} mode={mode} setDraftPoints={setDraftPoints} draftPoints={draftPoints} manualEdits={manualEdits} pending={pending} onExportReady={setMapActions} /></MapErrorBoundary>
        <button className="panel-toggle" onClick={() => setPanelOpen((open) => !open)} title={panelOpen ? "Collapse controls" : "Open controls"} aria-label={panelOpen ? "Collapse controls" : "Open controls"}>{panelOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}</button>
        <div className="legend" aria-label="Map legend">
          <span><i className="buildable" />Buildable</span>
          {layers.filter((layer) => layer.enabled).map((layer) => <span key={layer.id}><i style={{ background: LAYER_COLORS[layer.id] }} />{layer.label.replace("NWI ", "")}</span>)}
          <span><i className="manual" />Manual edit</span>
        </div>
        {pending && <div className="map-pending"><i className="spinner" />Updating analysis</div>}
        {tourStep !== null && <Walkthrough step={tourStep} onNext={() => setTourStep((step) => step + 1)} onClose={closeTour} />}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
