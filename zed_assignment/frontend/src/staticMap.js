export const STATIC_MAP_SIZE = Object.freeze({ width: 1000, height: 700, padding: 42 });

export function featuresFromGeoJSON(value) {
  if (!value) return [];
  if (value.type === "FeatureCollection") return value.features ?? [];
  if (value.type === "Feature") return [value];
  return [{ type: "Feature", properties: {}, geometry: value }];
}

function visitCoordinates(geometry, callback) {
  const visit = (coordinates) => {
    if (!Array.isArray(coordinates)) return;
    if (typeof coordinates[0] === "number") {
      callback(coordinates);
      return;
    }
    coordinates.forEach(visit);
  };
  visit(geometry?.coordinates);
}

export function boundsForGeoJSON(values) {
  const bounds = { minLng: Infinity, minLat: Infinity, maxLng: -Infinity, maxLat: -Infinity };
  values.flatMap(featuresFromGeoJSON).forEach((feature) => {
    visitCoordinates(feature.geometry, ([lng, lat]) => {
      bounds.minLng = Math.min(bounds.minLng, lng);
      bounds.minLat = Math.min(bounds.minLat, lat);
      bounds.maxLng = Math.max(bounds.maxLng, lng);
      bounds.maxLat = Math.max(bounds.maxLat, lat);
    });
  });
  return Number.isFinite(bounds.minLng) ? bounds : null;
}

export function createStaticProjector(bounds, size = STATIC_MAP_SIZE) {
  const lngSpan = Math.max(bounds.maxLng - bounds.minLng, 0.000001);
  const latSpan = Math.max(bounds.maxLat - bounds.minLat, 0.000001);
  const drawableWidth = size.width - size.padding * 2;
  const drawableHeight = size.height - size.padding * 2;
  const scale = Math.min(drawableWidth / lngSpan, drawableHeight / latSpan);
  const xOffset = (size.width - lngSpan * scale) / 2;
  const yOffset = (size.height - latSpan * scale) / 2;
  return {
    project([lng, lat]) {
      return [
        xOffset + (lng - bounds.minLng) * scale,
        size.height - (yOffset + (lat - bounds.minLat) * scale),
      ];
    },
    unproject([x, y]) {
      return {
        lng: bounds.minLng + (x - xOffset) / scale,
        lat: bounds.minLat + ((size.height - y) - yOffset) / scale,
      };
    },
  };
}

function ringToPath(ring, project) {
  return ring.map((coordinate, index) => {
    const [x, y] = project(coordinate);
    return `${index ? "L" : "M"}${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(" ") + " Z";
}

export function geometryToSvgPaths(geometry, project) {
  if (!geometry) return [];
  if (geometry.type === "Polygon") return [geometry.coordinates.map((ring) => ringToPath(ring, project)).join(" ")];
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates.map((polygon) => polygon.map((ring) => ringToPath(ring, project)).join(" "));
  }
  if (geometry.type === "LineString") {
    return [geometry.coordinates.map((coordinate, index) => {
      const [x, y] = project(coordinate);
      return `${index ? "L" : "M"}${x.toFixed(2)} ${y.toFixed(2)}`;
    }).join(" ")];
  }
  return [];
}
