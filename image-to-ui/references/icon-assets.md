# Icon Assets

Use the bundled Lucide static SVG collection as the default icon source for local HTML. The collection is stored under `assets/icons/lucide/` with its upstream version and license. Inline SVG is an output form; it does not identify the source. Record the resolver source separately in UI IR.

## Resolve an icon

Run:

```bash
node scripts/resolve-icon.mjs "settings" --json
node scripts/resolve-icon.mjs "设置" --inline
node scripts/resolve-icon.mjs "navigation" --copy-to /absolute/output/assets/icons
```

For canvas output, resolve icons in this order:

1. a concrete target-platform MCP resource or component, confirmed by target readback;
2. the bundled Lucide cache, through a target-supported vector route;
3. an approved Material Symbols asset, version-pinned and supplied through a verified target route;
4. a deterministic vector drawing from basic primitives;
5. a circular placeholder for a non-critical icon, explicitly marked and reported.

For every local-HTML icon, call `resolve-icon.mjs --inline` first. Resolve the bundled static cache in this order: `overrides/<name>.svg`, aliases in `aliases.json`, upstream Lucide filenames, then Lucide semantic tags. When resolved, keep the returned SVG geometry, copy the resolved SVG into the canonical output asset package for lineage, and record `assetId: "lucide:<resolved-name>"`, `assetAction: "resolve-icon"`, and `provenance: "local-library"`; add matching `data-asset-id` and `data-icon-source` attributes to the inline `<svg>`. The inline geometry must match the recorded canonical Lucide asset. Do not hand-author a substitute SVG for a matchable icon.

If the resolver exits with code `2`, record `iconResolution: {"lucideAttempted": true, "status": "unresolved", "reason": "..."}` before using a local version-pinned fallback. For a visual mark that is intentionally not a generic UI icon, record status `not-applicable` and the reason. Never infer canvas-native editability from the existence of an SVG file.

## Modify or replace

- Replace one icon without editing the upstream cache by adding an SVG with the same filename to `assets/icons/lucide/overrides/`.
- Add or change semantic mappings in `assets/icons/lucide/aliases.json`.
- Keep the SVG `viewBox`; use `currentColor` for configurable color where appropriate.
- When upgrading Lucide, replace `icons/`, `tags.json`, `LICENSE`, and `package.json` together. Preserve `overrides/` and `aliases.json`.

## HTML output

Use `--inline` and insert the returned SVG markup directly into static HTML. The final HTML is self-contained, so do not reference an external SVG file. Do not add Lucide runtime JavaScript, icon fonts, characters, Emoji, or a CDN dependency.

### Uniform-scale icon sizing

For `targets.html.layoutMode: "uniform-scale"`, wrap every inline SVG in an icon container that has an explicit width and height in the root design space. Use `cqw`, `cqh`, normalized percentages, or an equivalent calculation from those units; do not use a final `px`, `rem`, `em`, or viewport size. Give every inline SVG this shared rule:

```css
svg {
  display: block;
  width: 100%;
  height: 100%;
}
```

Keep the SVG's source `width="24" height="24"` when it is part of the cached Lucide geometry, but never let those attributes determine its rendered dimensions. The wrapper is the `data-node-id` owner; keep `data-asset-id` and `data-icon-source` on its inline SVG so lineage and geometry checks remain intact.

Apply this pattern to every icon node, including nested spans, status-bar icons, card actions, repeated Dock icons, media controls, map controls, and HVAC/fan marks. A generic class such as `.icon-box` is acceptable only when each instance has explicit design-space dimensions; add a component-specific wrapper rule when sizes differ.

### Explicit preview-only Zoom

Add Zoom only when the user explicitly requests image-like preview scaling. Record it under `targets.html.previewZoom` as `{ "enabled": true, "minPercent": 50, "maxPercent": 200, "stepPercent": 10 }`; omit the field otherwise. Put the transform on one wrapper around the complete fixed-ratio root canvas, keep the root and every UI node unmodified, and retain one copy of every node and asset.

When enabled, the preview page may handle Cmd/Ctrl + `-`, `+`, and `0` only while the preview page has focus, prevent the browser default for those handled keys, and apply the configured step or reset to the wrapper. Do not add buttons, product behavior, navigation, playback, animation, or Zoom behavior to canvas targets. Zoom is preview behavior only and must not change UI IR bounds, source/target normalization, asset metadata, or canvas coordinates.

This library is an HTML asset source. Its presence does not prove that MasterGo or Figma will import the SVG as a native editable vector; canvas adapters must still inspect and verify their target route.
