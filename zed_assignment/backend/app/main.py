from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .area import analyze_buildable_area
from .sample_data import SAMPLE


class ConstraintLayer(BaseModel):
    id: str
    label: str
    reason: str
    setback_m: float = Field(default=0, ge=0, le=1000)
    features: list[dict[str, Any]]


class AnalysisRequest(BaseModel):
    parcel: dict[str, Any]
    constraints: list[ConstraintLayer]
    manual_exclusions: list[dict[str, Any]] = []
    manual_restores: list[dict[str, Any]] = []


app = FastAPI(title="Buildable Land Analysis", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sample")
def sample() -> dict[str, Any]:
    return SAMPLE


@app.post("/api/analyze")
def analyze(request: AnalysisRequest) -> dict[str, Any]:
    return analyze_buildable_area(
        parcel=request.parcel,
        constraints=[constraint.model_dump() for constraint in request.constraints],
        manual_exclusions=request.manual_exclusions,
        manual_restores=request.manual_restores,
    )
