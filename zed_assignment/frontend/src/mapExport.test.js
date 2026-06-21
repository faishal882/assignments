import assert from "node:assert/strict";
import test from "node:test";

import { captureMapCanvas, MAP_CANVAS_CONTEXT_ATTRIBUTES } from "./mapExport.js";

test("preserves the WebGL drawing buffer for map exports", () => {
  assert.equal(MAP_CANVAS_CONTEXT_ATTRIBUTES.preserveDrawingBuffer, true);
});

test("captures only after MapLibre renders a requested frame", async () => {
  let renderCallback;
  let repaintRequested = false;
  const map = {
    loaded: () => true,
    areTilesLoaded: () => true,
    once(event, callback) {
      assert.equal(event, "render");
      renderCallback = callback;
    },
    triggerRepaint() {
      repaintRequested = true;
      renderCallback();
    },
    getCanvas() {
      return { toDataURL: () => "data:image/png;base64,rendered-map" };
    },
  };

  const image = await captureMapCanvas(map);

  assert.equal(repaintRequested, true);
  assert.equal(image, "data:image/png;base64,rendered-map");
});

test("waits for pending map tiles before requesting the export frame", async () => {
  const events = [];
  const callbacks = {};
  const map = {
    loaded: () => false,
    areTilesLoaded: () => false,
    once(event, callback) {
      events.push(event);
      callbacks[event] = callback;
    },
    off() {},
    triggerRepaint() {
      events.push("repaint");
      callbacks.render();
    },
    getCanvas: () => ({ toDataURL: () => "data:image/png;base64,complete-map" }),
  };

  const capture = captureMapCanvas(map);
  assert.deepEqual(events, ["idle"]);
  callbacks.idle();

  assert.equal(await capture, "data:image/png;base64,complete-map");
  assert.deepEqual(events, ["idle", "render", "repaint"]);
});
