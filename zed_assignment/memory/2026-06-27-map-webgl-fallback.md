# Debug Report: Map WebGL Fallback

- **Symptom:** The map panel rendered as an empty/unavailable map in a browser environment where screenshots were being taken.
- **Root cause:** MapLibre requires a working WebGL context. The failing environment could not start WebGL, so the app correctly loaded parcel/API data but replaced the map with the existing non-visual fallback.
- **Fix:** Added a static SVG map fallback that projects parcel, buildable, excluded, constraint, manual edit, ghost, and draft geometries without WebGL. Drawing still records points in fallback mode.
- **Evidence:** Reproduced with `google-chrome --headless=new --disable-gpu`; after the fix the same command rendered parcel/buildable geometry instead of the unavailable-map message.
- **Regression test:** `frontend/src/staticMap.test.js` covers stable polygon projection and reverse projection.
- **Verification:** `npm run test --workspace frontend`, `npm run build`, and `npm test` passed.
- **Status:** DONE
