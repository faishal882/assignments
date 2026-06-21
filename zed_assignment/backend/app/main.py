from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from starlette.middleware.gzip import GZipMiddleware

from .area import analyze_buildable_area, buffer_cache, preview_constraint_layer
from .repository import repository


class LayerSelection(BaseModel):
    id: str
    enabled: bool = True
    setback_m: float | None = Field(default=None, ge=0, le=1609.344)


class ManualEdit(BaseModel):
    id: str
    label: str = Field(min_length=1, max_length=80)
    geometry: dict[str, Any]
    kind: Literal["carve-out", "restore"]


class AnalysisRequest(BaseModel):
    parcel_id: str | None = None
    parcel: dict[str, Any] | None = None
    layers: list[LayerSelection] | None = None
    manual_edits: list[ManualEdit] = Field(default_factory=list)
    policy_profile: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def require_one_parcel(self):
        if bool(self.parcel_id) == bool(self.parcel):
            raise ValueError("Provide exactly one of parcel_id or parcel")
        return self


app = FastAPI(
    title="Buildable Area Analysis API",
    version="1.0.0",
    description="Parcel-scale planning analysis. Results are not survey or legal determinations.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/layers")
def layers() -> dict[str, Any]:
    return {"layers": repository.layer_metadata(), **repository.policy_metadata()}


@app.get("/api/parcels/search")
def search_parcels(
    q: str = Query(default="", max_length=100),
    bbox: str | None = Query(default=None, description="west,south,east,north"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    try:
        parsed_bbox = tuple(float(value) for value in bbox.split(",")) if bbox else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="bbox must contain four numbers") from exc
    if parsed_bbox and len(parsed_bbox) != 4:
        raise HTTPException(status_code=422, detail="bbox must contain four numbers")
    parcels, total = repository.search_parcels(q, parsed_bbox, limit, offset)
    return {
        "parcels": parcels,
        "total": total,
        "limit": limit,
        "offset": offset,
        "featured_parcel_id": repository.featured_parcel_id(),
    }


@app.get("/api/parcels/{parcel_id}")
def parcel(parcel_id: str) -> dict[str, Any]:
    found = repository.get_parcel(parcel_id)
    if not found:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return found


@app.get("/api/parcels/{parcel_id}/outline")
def parcel_outline(parcel_id: str) -> dict[str, Any]:
    found = repository.get_parcel_outline(parcel_id)
    if not found:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return found


@app.post("/api/analyze/preview")
def analyze_preview(request: AnalysisRequest) -> dict[str, Any]:
    if not request.layers or len(request.layers) != 1:
        raise HTTPException(status_code=422, detail="Preview requires exactly one layer")
    parcel_feature = request.parcel or repository.get_parcel(request.parcel_id or "")
    if not parcel_feature:
        raise HTTPException(status_code=404, detail="Parcel not found")
    started = perf_counter()
    try:
        constraints = repository.resolve_layers(
            request.layers, parcel_feature, request.policy_profile
        )
        if not constraints:
            raise ValueError("Preview layer must be enabled")
        constraint = constraints[0]
        result = preview_constraint_layer(parcel_feature, constraint)
        result["duration_ms"] = round((perf_counter() - started) * 1000, 2)
        return result
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown layer: {exc.args[0]}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/analyze")
def analyze(request: AnalysisRequest) -> dict[str, Any]:
    parcel_feature = request.parcel or repository.get_parcel(request.parcel_id or "")
    if not parcel_feature:
        raise HTTPException(status_code=404, detail="Parcel not found")
    started = perf_counter()
    try:
        constraints = repository.resolve_layers(request.layers, parcel_feature, request.policy_profile)
        carve_outs = [edit.geometry for edit in request.manual_edits if edit.kind == "carve-out"]
        restores = [edit.geometry for edit in request.manual_edits if edit.kind == "restore"]
        result = analyze_buildable_area(parcel_feature, constraints, carve_outs, restores)
        result["analysis_id"] = str(uuid4())
        result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
        result["policy"] = repository.analysis_policy(request.policy_profile, constraints)
        result["duration_ms"] = round((perf_counter() - started) * 1000, 2)
        return result
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown layer: {exc.args[0]}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/performance/cache")
def cache_performance() -> dict[str, Any]:
    return {
        "buffer_cache": buffer_cache.stats(),
        "ttl_seconds": buffer_cache.ttl_seconds,
        "max_entries": buffer_cache.max_entries,
    }
