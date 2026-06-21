from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from shapely.geometry import box, mapping, shape


SCHEMA = """
CREATE TABLE IF NOT EXISTS parcels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL DEFAULT '',
    county TEXT NOT NULL DEFAULT '',
    properties TEXT NOT NULL,
    geometry TEXT NOT NULL,
    display_geometry TEXT,
    minx REAL NOT NULL, miny REAL NOT NULL, maxx REAL NOT NULL, maxy REAL NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS parcel_rtree USING rtree(
    rowid, minx, maxx, miny, maxy
);
CREATE TABLE IF NOT EXISTS constraints (
    id INTEGER PRIMARY KEY,
    layer_id TEXT NOT NULL,
    properties TEXT NOT NULL,
    geometry TEXT NOT NULL,
    display_geometry TEXT,
    region_id TEXT NOT NULL DEFAULT '',
    minx REAL NOT NULL, miny REAL NOT NULL, maxx REAL NOT NULL, maxy REAL NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS constraint_rtree USING rtree(
    id, minx, maxx, miny, maxy
);
CREATE INDEX IF NOT EXISTS constraints_layer_idx ON constraints(layer_id);
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


class SpatialStore:
    def __init__(self, path: Path):
        self.path = path
        self._column_cache: dict[str, set[str]] = {}

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def _columns(self, table: str) -> set[str]:
        if table not in self._column_cache:
            with self.connect() as connection:
                self._column_cache[table] = {
                    row[1] for row in connection.execute(f"PRAGMA table_info({table})")
                }
        return self._column_cache[table]

    def replace_parcels(self, features: Iterable[dict[str, Any]], display_tolerance: float = 0.000005) -> int:
        count = 0
        with self.connect() as connection:
            connection.execute("DELETE FROM parcel_rtree")
            connection.execute("DELETE FROM parcels")
            for index, feature in enumerate(features, start=1):
                geometry = shape(feature["geometry"])
                if geometry.is_empty or geometry.geom_type not in {"Polygon", "MultiPolygon"}:
                    continue
                properties = feature.get("properties", {})
                source_id = str(
                    properties.get("id")
                    or properties.get("PROP_ID")
                    or properties.get("prop_id")
                    or properties.get("GEO_ID")
                    or properties.get("geo_id")
                    or index
                ).strip()
                source_object_id = str(
                    properties.get("FID") or properties.get("OBJECTID") or feature.get("id") or index
                ).strip()
                fips = str(properties.get("FIPS") or properties.get("fips") or "48").strip()
                parcel_id = source_id if properties.get("id") else f"TNRIS-{fips}-{source_id}-{source_object_id}"
                county = str(properties.get("county") or properties.get("COUNTY") or "").title()
                address = str(properties.get("address") or properties.get("SITUS_ADDR") or "").strip()
                legal_description = str(properties.get("LEGAL_DESC") or properties.get("legal_desc") or "").strip()
                name = str(properties.get("name") or address or legal_description or f"{county} parcel {parcel_id}").strip()[:100]
                minx, miny, maxx, maxy = geometry.bounds
                display_geometry = geometry.simplify(display_tolerance, preserve_topology=True)
                connection.execute(
                    "INSERT INTO parcels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (parcel_id, name, address, county, json.dumps(properties), json.dumps(mapping(geometry)), json.dumps(mapping(display_geometry)), minx, miny, maxx, maxy),
                )
                rowid = connection.execute("SELECT rowid FROM parcels WHERE id = ?", (parcel_id,)).fetchone()[0]
                connection.execute("INSERT INTO parcel_rtree VALUES (?, ?, ?, ?, ?)", (rowid, minx, maxx, miny, maxy))
                count += 1
        return count

    def replace_constraints(
        self,
        layer_id: str,
        features: Iterable[dict[str, Any]],
        region_id: str = "",
        display_tolerance: float = 0.00001,
    ) -> int:
        count = 0
        with self.connect() as connection:
            old_ids = [row[0] for row in connection.execute("SELECT id FROM constraints WHERE layer_id = ?", (layer_id,))]
            connection.executemany("DELETE FROM constraint_rtree WHERE id = ?", ((item,) for item in old_ids))
            connection.execute("DELETE FROM constraints WHERE layer_id = ?", (layer_id,))
            for feature in features:
                geometry = shape(feature["geometry"])
                if geometry.is_empty:
                    continue
                minx, miny, maxx, maxy = geometry.bounds
                display_geometry = geometry.simplify(display_tolerance, preserve_topology=True)
                cursor = connection.execute(
                    "INSERT INTO constraints(layer_id, properties, geometry, display_geometry, region_id, minx, miny, maxx, maxy) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (layer_id, json.dumps(feature.get("properties", {})), json.dumps(mapping(geometry)), json.dumps(mapping(display_geometry)), region_id, minx, miny, maxx, maxy),
                )
                connection.execute("INSERT INTO constraint_rtree VALUES (?, ?, ?, ?, ?)", (cursor.lastrowid, minx, maxx, miny, maxy))
                count += 1
        return count

    def get_parcel(self, parcel_id: str, display: bool = False) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM parcels WHERE id = ?", (parcel_id,)).fetchone()
        return self._parcel_feature(row, display) if row else None

    def search_parcels(self, query: str, bounds=None, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        filters = []
        values: list[Any] = []
        join = ""
        if query:
            filters.append("(p.id LIKE ? OR p.name LIKE ? OR p.address LIKE ?)")
            term = f"%{query}%"
            values.extend([term, term, term])
        if bounds:
            join = "JOIN parcel_rtree r ON r.rowid = p.rowid"
            filters.append("r.minx <= ? AND r.maxx >= ? AND r.miny <= ? AND r.maxy >= ?")
            minx, miny, maxx, maxy = bounds
            values.extend([maxx, minx, maxy, miny])
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        with self.connect() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM parcels p {join} {where}", values).fetchone()[0]
            rows = connection.execute(
                f"SELECT p.* FROM parcels p {join} {where} ORDER BY p.name, p.id LIMIT ? OFFSET ?",
                [*values, limit, offset],
            ).fetchall()
        return [self._parcel_summary(row) for row in rows], total

    def constraints_for_bounds(self, layer_id: str, bounds, display: bool = False) -> list[dict[str, Any]]:
        minx, miny, maxx, maxy = bounds
        has_display = "display_geometry" in self._columns("constraints")
        geometry_column = "c.display_geometry" if display and has_display else "c.geometry"
        with self.connect() as connection:
            rows = connection.execute(
                f"""SELECT c.properties, {geometry_column} AS geometry FROM constraints c
                JOIN constraint_rtree r ON r.id = c.id
                WHERE c.layer_id = ? AND r.minx <= ? AND r.maxx >= ?
                  AND r.miny <= ? AND r.maxy >= ?""",
                (layer_id, maxx, minx, maxy, miny),
            ).fetchall()
        return [
            {"type": "Feature", "properties": json.loads(row["properties"]), "geometry": json.loads(row["geometry"])}
            for row in rows
        ]

    def metadata(self, key: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def _parcel_feature(self, row: sqlite3.Row, display: bool = False) -> dict[str, Any]:
        properties = json.loads(row["properties"])
        properties.update({"id": row["id"], "name": row["name"], "address": row["address"], "county": row["county"]})
        geometry_key = "display_geometry" if display and "display_geometry" in self._columns("parcels") and row["display_geometry"] else "geometry"
        return {"type": "Feature", "properties": properties, "geometry": json.loads(row[geometry_key])}

    @staticmethod
    def _parcel_summary(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "name": row["name"], "address": row["address"], "county": row["county"],
            "bbox": [row["minx"], row["miny"], row["maxx"], row["maxy"]],
        }
