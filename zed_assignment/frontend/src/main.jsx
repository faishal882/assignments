import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import L from "leaflet";
import { Check, Minus, Plus, RotateCcw, Trash2 } from "lucide-react";
import "leaflet/dist/leaflet.css";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

function featureCollection(features = []) {
  return { type: "FeatureCollection", features: features.filter(Boolean) };
}

function getBounds(features) {
  const coords = [];
  const visit = (value) => {
    if (!Array.isArray(value)) return;
    if (typeof value[0] === "number" && typeof value[1] === "number") {
      coords.push([value[1], value[0]]);
      return;
    }
    value.forEach(visit);
  };
  features.forEach((feature) => visit(feature?.geometry?.coordinates));
  return coords.length ? L.latLngBounds(coords) : null;
}

function polygonFeature(points) {
  const ring = points.map((point) => [point.lng, point.lat]);
  ring.push(ring[0]);
  return {
    type: "Feature",
    properties: {},
    geometry: { type: "Polygon", coordinates: [ring] },
  };
}

function MapView({ sample, result, mode, draftPoints, setDraftPoints, manualExclusions, manualRestores }) {
  const mapRef = useRef(null);
  const layerRef = useRef(L.layerGroup());

  useEffect(() => {
    if (mapRef.current) return;
    const map = L.map("map", { zoomControl: true }).setView([30.2755, -97.7342], 15);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 20,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
    layerRef.current.addTo(map);
    mapRef.current = map;
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const handleClick = (event) => {
      if (!mode) return;
      setDraftPoints((points) => [...points, event.latlng]);
    };
    map.on("click", handleClick);
    return () => map.off("click", handleClick);
  }, [mode, setDraftPoints]);

  useEffect(() => {
    const map = mapRef.current;
    const layers = layerRef.current;
    if (!map || !sample || !result) return;
    layers.clearLayers();

    L.geoJSON(sample.parcel, {
      style: { color: "#202124", weight: 2, fillOpacity: 0 },
    }).addTo(layers);
    L.geoJSON(result.features.excluded, {
      style: { color: "#b42318", fillColor: "#f04438", weight: 1, fillOpacity: 0.38 },
    }).addTo(layers);
    L.geoJSON(result.features.buildable, {
      style: { color: "#067647", fillColor: "#12b76a", weight: 1, fillOpacity: 0.5 },
    }).addTo(layers);
    L.geoJSON(result.features.constraints, {
      style: { color: "#7a5af8", fillColor: "#7a5af8", weight: 1, fillOpacity: 0.2 },
    }).addTo(layers);
    L.geoJSON(featureCollection(manualExclusions), {
      style: { color: "#7f1d1d", fillColor: "#dc2626", dashArray: "4 4", weight: 2, fillOpacity: 0.28 },
    }).addTo(layers);
    L.geoJSON(featureCollection(manualRestores), {
      style: { color: "#14532d", fillColor: "#22c55e", dashArray: "4 4", weight: 2, fillOpacity: 0.28 },
    }).addTo(layers);

    if (draftPoints.length > 0) {
      const latLngs = draftPoints.map((point) => [point.lat, point.lng]);
      L.polyline(latLngs, { color: mode === "exclude" ? "#991b1b" : "#166534", weight: 3 }).addTo(layers);
      draftPoints.forEach((point) => {
        L.circleMarker(point, {
          radius: 5,
          color: "#111827",
          fillColor: "#ffffff",
          fillOpacity: 1,
          weight: 2,
        }).addTo(layers);
      });
    }

    const bounds = getBounds([sample.parcel]);
    if (bounds && !map._buildableFitDone) {
      map.fitBounds(bounds.pad(0.15));
      map._buildableFitDone = true;
    }
  }, [sample, result, draftPoints, mode, manualExclusions, manualRestores]);

  return <div id="map" aria-label="Buildable land map" />;
}

function App() {
  const [sample, setSample] = useState(null);
  const [constraints, setConstraints] = useState([]);
  const [result, setResult] = useState(null);
  const [manualExclusions, setManualExclusions] = useState([]);
  const [manualRestores, setManualRestores] = useState([]);
  const [mode, setMode] = useState(null);
  const [draftPoints, setDraftPoints] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/api/sample`)
      .then((response) => response.json())
      .then((data) => {
        setSample(data);
        setConstraints(data.constraints);
      })
      .catch(() => setError("Could not load sample data from the backend."));
  }, []);

  const request = useMemo(() => {
    if (!sample) return null;
    return {
      parcel: sample.parcel,
      constraints,
      manual_exclusions: manualExclusions,
      manual_restores: manualRestores,
    };
  }, [sample, constraints, manualExclusions, manualRestores]);

  useEffect(() => {
    if (!request) return;
    fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
      .then((response) => {
        if (!response.ok) throw new Error("analysis failed");
        return response.json();
      })
      .then((data) => {
        setError("");
        setResult(data);
      })
      .catch(() => setError("Analysis failed. Check that the FastAPI server is running."));
  }, [request]);

  const startMode = (nextMode) => {
    setMode(nextMode);
    setDraftPoints([]);
  };

  const finishPolygon = () => {
    if (draftPoints.length < 3 || !mode) return;
    const feature = polygonFeature(draftPoints);
    if (mode === "exclude") setManualExclusions((items) => [...items, feature]);
    if (mode === "restore") setManualRestores((items) => [...items, feature]);
    setDraftPoints([]);
    setMode(null);
  };

  const updateSetback = (id, value) => {
    setConstraints((items) =>
      items.map((item) => (item.id === id ? { ...item, setback_m: Number(value) } : item)),
    );
  };

  return (
    <main className="shell">
      <section className="sidebar">
        <div className="brand">
          <span>Buildable Land Analysis</span>
          <strong>{result ? `${result.buildable_acres} ac` : "--"}</strong>
        </div>

        {result && (
          <div className="metrics">
            <div>
              <span>Parcel</span>
              <strong>{result.parcel_acres} ac</strong>
            </div>
            <div>
              <span>Buildable exact</span>
              <strong>{result.buildable_acres_exact} ac</strong>
            </div>
            <div>
              <span>Excluded</span>
              <strong>{result.excluded_acres} ac</strong>
            </div>
          </div>
        )}

        <div className="toolbar" aria-label="Manual edit tools">
          <button className={mode === "exclude" ? "active danger" : "danger"} onClick={() => startMode("exclude")} title="Draw carve-out">
            <Minus size={16} /> Carve
          </button>
          <button className={mode === "restore" ? "active success" : "success"} onClick={() => startMode("restore")} title="Draw restore area">
            <Plus size={16} /> Restore
          </button>
          <button onClick={finishPolygon} disabled={draftPoints.length < 3} title="Finish polygon">
            <Check size={16} /> Finish
          </button>
          <button onClick={() => setDraftPoints([])} disabled={!draftPoints.length} title="Clear current sketch">
            <RotateCcw size={16} />
          </button>
          <button
            onClick={() => {
              setManualExclusions([]);
              setManualRestores([]);
              setDraftPoints([]);
              setMode(null);
            }}
            title="Clear manual edits"
          >
            <Trash2 size={16} />
          </button>
        </div>

        {mode && <p className="hint">Click the map to place polygon vertices.</p>}
        {error && <p className="error">{error}</p>}

        <h2>Setbacks</h2>
        <div className="setbacks">
          {constraints.map((constraint) => (
            <label key={constraint.id}>
              <span>{constraint.label}</span>
              <input
                type="number"
                min="0"
                max="1000"
                value={constraint.setback_m}
                onChange={(event) => updateSetback(constraint.id, event.target.value)}
              />
              <small>m</small>
            </label>
          ))}
        </div>

        <h2>Breakdown</h2>
        <div className="breakdown">
          {result?.breakdown.map((row) => (
            <div key={row.id} className="breakdown-row">
              <div>
                <strong>{row.label}</strong>
                <span>{row.reason}</span>
              </div>
              <b>{row.removed_acres} ac</b>
            </div>
          ))}
        </div>
      </section>

      <section className="map-panel">
        <MapView
          sample={sample}
          result={result}
          mode={mode}
          draftPoints={draftPoints}
          setDraftPoints={setDraftPoints}
          manualExclusions={manualExclusions}
          manualRestores={manualRestores}
        />
        <div className="legend">
          <span><i className="buildable" /> Buildable</span>
          <span><i className="excluded" /> Excluded</span>
          <span><i className="constraint" /> Constraint buffers</span>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
