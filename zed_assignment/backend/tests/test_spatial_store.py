import sqlite3

from shapely.geometry import Polygon, mapping

from app.spatial_store import SpatialStore


def polygon_feature(identifier: str):
    coordinates = [
        (-97.45, 31.06),
        (-97.44, 31.06),
        (-97.44, 31.07),
        (-97.45, 31.07),
        (-97.45, 31.06),
    ]
    return {
        "type": "Feature",
        "properties": {"id": identifier, "name": identifier},
        "geometry": mapping(Polygon(coordinates)),
    }


def test_new_catalog_stores_full_and_display_geometries_with_rtree(tmp_path):
    store = SpatialStore(tmp_path / "catalog.sqlite")
    store.initialize()
    feature = polygon_feature("parcel-1")

    assert store.replace_parcels([feature]) == 1
    assert store.replace_constraints("wetlands", [feature], region_id="bell") == 1

    assert store.get_parcel("parcel-1")["geometry"]
    assert store.get_parcel("parcel-1", display=True)["geometry"]
    assert len(store.constraints_for_bounds("wetlands", (-98, 30, -97, 32))) == 1
    with sqlite3.connect(store.path) as connection:
        row = connection.execute(
            "SELECT region_id, display_geometry FROM constraints"
        ).fetchone()
        rtree_count = connection.execute("SELECT COUNT(*) FROM constraint_rtree").fetchone()[0]
    assert row[0] == "bell"
    assert row[1]
    assert rtree_count == 1
