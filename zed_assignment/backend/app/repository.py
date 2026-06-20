"""Small file-backed repository used by the runnable demo.

The interface intentionally matches what a PostGIS implementation would expose:
parcel lookup/search, public layer metadata, and parcel-scoped layer selection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shapely.geometry import box, shape
from shapely.strtree import STRtree

from .sample_data import PARCELS, SOURCE_FEATURES
from .spatial_store import SpatialStore

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"
CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.sqlite"


class Repository:
    def __init__(self):
        self.config = json.loads(CONFIG_PATH.read_text())
        self._layers = {layer["id"]: layer for layer in self.config["layers"]}
        self._profiles = {profile["id"]: profile for profile in self.config["profiles"]}
        self._validate_config()
        self._feature_lists = {layer_id: list(features) for layer_id, features in SOURCE_FEATURES.items()}
        self._geometries = {
            layer_id: [shape(feature["geometry"]) for feature in features]
            for layer_id, features in self._feature_lists.items()
        }
        self._indexes = {
            layer_id: STRtree(geometries) for layer_id, geometries in self._geometries.items()
        }
        self.store = SpatialStore(CATALOG_PATH) if CATALOG_PATH.exists() else None

    def layer_metadata(self) -> list[dict[str, Any]]:
        return [dict(layer) for layer in self.config["layers"]]

    def policy_metadata(self) -> dict[str, Any]:
        return {
            "config_version": self.config["config_version"],
            "jurisdiction": self.config["jurisdiction"],
            "disclaimer": self.config["disclaimer"],
            "default_profile": self.config["default_profile"],
            "profiles": [dict(profile) for profile in self.config["profiles"]],
        }

    def _validate_config(self) -> None:
        if self.config.get("default_profile") not in self._profiles:
            raise ValueError("default_profile must reference a configured profile")
        layer_ids = set(self._layers)
        for profile in self._profiles.values():
            if set(profile.get("setbacks_m", {})) != layer_ids:
                raise ValueError(f"Profile {profile['id']} must configure every layer")
        for layer in self._layers.values():
            if not 0 <= layer["default_setback_m"] <= layer["max_setback_m"]:
                raise ValueError(f"Invalid default setback for {layer['id']}")

    def featured_parcel_id(self) -> str | None:
        return self.store.metadata("featured_parcel_id") if self.store else "TCAD-0315310103"

    def get_parcel(self, parcel_id: str) -> dict[str, Any] | None:
        return (self.store.get_parcel(parcel_id) if self.store else None) or PARCELS.get(parcel_id)

    def search_parcels(self, query: str, bbox_values=None, limit=50, offset=0) -> tuple[list[dict[str, Any]], int]:
        if self.store:
            return self.store.search_parcels(query.strip(), bbox_values, limit, offset)
        query = query.casefold().strip()
        bounds = box(*bbox_values) if bbox_values else None
        results = []
        for parcel_id, feature in PARCELS.items():
            props = feature["properties"]
            searchable = " ".join([parcel_id, props.get("name", ""), props.get("address", "")]).casefold()
            if query and query not in searchable:
                continue
            if bounds and not shape(feature["geometry"]).intersects(bounds):
                continue
            results.append({"id": parcel_id, **props, "bbox": list(shape(feature["geometry"]).bounds)})
        return results[offset:offset + limit], len(results)

    def resolve_layers(self, selections, parcel: dict[str, Any] | None = None, profile_id: str | None = None) -> list[dict[str, Any]]:
        profile_id = profile_id or self.config["default_profile"]
        if profile_id not in self._profiles:
            raise ValueError(f"Unknown policy profile: {profile_id}")
        profile = self._profiles[profile_id]
        selected = selections or [
            type("DefaultSelection", (), {"id": layer_id, "enabled": True, "setback_m": None})
            for layer_id in self._layers
        ]
        resolved = []
        for selection in selected:
            if not selection.enabled:
                continue
            metadata = self._layers[selection.id]
            setback_m = profile["setbacks_m"][selection.id] if selection.setback_m is None else selection.setback_m
            if not metadata["min_setback_m"] <= setback_m <= metadata["max_setback_m"]:
                raise ValueError(
                    f"{selection.id} setback must be between {metadata['min_setback_m']} and {metadata['max_setback_m']} metres"
                )
            features = self._feature_lists.get(selection.id, [])
            is_fixture = parcel and parcel.get("properties", {}).get("id") in PARCELS
            if self.store and parcel and not is_fixture:
                parcel_bounds = shape(parcel["geometry"]).bounds
                features = self.store.constraints_for_bounds(selection.id, parcel_bounds)
            if (not self.store or is_fixture) and parcel and features:
                # Geographic pre-filter only; exact clipping and all measurements
                # still happen in the projected geometry engine.
                search_geometry = shape(parcel["geometry"]).buffer(float(setback_m) / 100_000)
                candidate_indexes = self._indexes[selection.id].query(search_geometry)
                features = [features[int(index)] for index in candidate_indexes]
            resolved.append(
                {
                    **metadata,
                    "setback_m": setback_m,
                    "features": features,
                }
            )
        return resolved

    def analysis_policy(self, profile_id: str | None, constraints: list[dict[str, Any]]) -> dict[str, Any]:
        selected_profile = profile_id or self.config["default_profile"]
        return {
            "config_version": self.config["config_version"],
            "profile_id": selected_profile,
            "jurisdiction": self.config["jurisdiction"],
            "disclaimer": self.config["disclaimer"],
            "assumptions": [
                {
                    key: constraint[key]
                    for key in ("id", "label", "setback_m", "geometry_basis", "basis", "verification", "source", "source_url", "guidance_url")
                }
                for constraint in constraints
            ],
        }


repository = Repository()
