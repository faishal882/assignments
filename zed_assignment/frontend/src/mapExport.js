export const MAP_CANVAS_CONTEXT_ATTRIBUTES = Object.freeze({
  preserveDrawingBuffer: true,
});

function waitForMapIdle(map, timeoutMs) {
  const loaded = typeof map.loaded !== "function" || map.loaded();
  const tilesLoaded = typeof map.areTilesLoaded !== "function" || map.areTilesLoaded();
  if (loaded && tilesLoaded) return Promise.resolve();
  return new Promise((resolve) => {
    const finish = () => {
      clearTimeout(timer);
      map.off?.("idle", finish);
      resolve();
    };
    const timer = setTimeout(finish, timeoutMs);
    map.once("idle", finish);
  });
}

export async function captureMapCanvas(map, timeoutMs = 3000) {
  await waitForMapIdle(map, timeoutMs);
  return new Promise((resolve, reject) => {
    map.once("render", () => {
      try {
        const image = map.getCanvas().toDataURL("image/png");
        if (!image || image === "data:,") throw new Error("Map canvas returned no image data");
        resolve(image);
      } catch (error) {
        reject(error);
      }
    });
    map.triggerRepaint();
  });
}
