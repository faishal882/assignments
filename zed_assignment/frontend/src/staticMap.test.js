import test from "node:test";
import assert from "node:assert/strict";
import { boundsForGeoJSON, createStaticProjector, featuresFromGeoJSON, geometryToSvgPaths } from "./staticMap.js";

test("projects parcel polygons into stable SVG paths", () => {
  const parcel = {
    type: "Feature",
    properties: { id: "parcel-1" },
    geometry: {
      type: "Polygon",
      coordinates: [[[-97.1, 31.1], [-97.0, 31.1], [-97.0, 31.2], [-97.1, 31.2], [-97.1, 31.1]]],
    },
  };
  const bounds = boundsForGeoJSON([parcel]);
  const projector = createStaticProjector(bounds);
  const paths = geometryToSvgPaths(parcel.geometry, projector.project);

  assert.equal(featuresFromGeoJSON(parcel).length, 1);
  assert.equal(paths.length, 1);
  assert.match(paths[0], /^M/);
  assert.match(paths[0], /Z$/);
  assert.deepEqual(projector.unproject(projector.project([-97.05, 31.15])), { lng: -97.05, lat: 31.15 });
});
