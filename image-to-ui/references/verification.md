# Lightweight Verification

Verification protects the primary deliverable from obvious omissions. It is not a second design or development project.

## Before writing

Perform a quick target-resource preflight:

- confirm the locked reference has complete Screen metadata and component-grouped five-column tables generated after its most recent image-generation/edit pass;
- confirm every presentation row maps to one or more existing UI IR nodes, every visible UI IR node is covered, and any `structuralOnly` node has a valid non-visible reason;
- confirm the target adapter is available;
- confirm required icon/component routes;
- confirm every local-HTML icon ran through the Lucide resolver or records an explicit unresolved/not-applicable attempt; resolved icons carry `lucide:<name>`, `resolve-icon`, and `local-library` metadata;
- confirm local image paths and basic image requirements;
- confirm the UI IR has been saved as `ui-ir.json` and every image-bearing node has an existing `assetPath`, `assetId`, dimensions, transparency status, `sourceCrop`, and `fitMode`;
- resolve the validator relative to the active image-to-ui skill directory, then run it once for the provisional HTML contract (or once with `--target <adapter>` before a canvas write); a non-zero exit blocks delivery and stops automatic repair by default. Do not use a repeated validator loop to drive visual changes;
- confirm HTML, MasterGo, or Figma verification used the canonical UI IR revision and asset registry, and that no target branch contains unregistered derived assets or a divergent node tree;
- confirm every conversational table edit is represented in the current `revision`/`changes` list and synchronized to its mapped UI IR nodes, assets, and HTML/canvas target mappings;
- resolve obvious unsupported representations before the primary write.

## After writing

Perform one short structural readback using the root or target identifier returned by the write operation. Check only:

- root exists;
- major regions exist;
- repeated element counts are not obviously wrong;
- visible text is present;
- non-semantic visual primitives are not represented as text: avatar facial features, dots, arrows, decorative marks, icons, and geometric markers must read back as shapes/vectors/paths or verified vector assets;
- icons are real target resources, target-verified vector routes, or explicitly marked external/placeholder fallbacks; do not infer editability from the source file extension;
- for MasterGo with two or more semantic icons, read each actual SVG/image resource from the returned root and fail the delivery if different meanings share one `./asset/icons/svg_*.svg` placeholder; repair the affected node with `agent_replace_node`, then inspect a screenshot where every Dock/tool-bar icon is visually distinguishable;
- image layers contain actual fills;
- every declared image asset exists on disk and is actually referenced by the generated HTML or canvas output; a conceptual raster asset without a saved file or provenance is a failure;
- for HTML, every `img src` and CSS `url(...)` data URL is traceable to the declared `assetId`/`assetPath` and matching local asset metadata; local file references are allowed only when explicitly requested or required by the target adapter. The complete UI reference must not be reused as the visible content of unrelated image nodes;
- for HTML, every visible node has one matching `data-node-id`, every raster-bearing element has the canonical `data-asset-id`, and visible text is mapped to its UI IR text node rather than introduced as an unmapped convenience label or CSS pseudo-content;
- for uniform-scale HTML, every inline SVG has the shared `display:block; width:100%; height:100%` rule and an immediately enclosing icon container with explicit root-design-space width and height; inspect status-bar, nested, card, media, map, HVAC, and repeated navigation icons rather than sampling only one group;
- when `targets.html.previewZoom.enabled` is true, verify that one preview-only wrapper scales the complete root canvas, keyboard handling is scoped to the focused preview, and no UI IR geometry, asset, or canvas coordinate changes;
- the result was not flattened into the full-screen reference image.
- when a `参考保真视觉底图` is used, it is the bottom-most layer, has exact canvas dimensions and aspect ratio, is placed at `100% × 100%` without stretching, contains no controls that should be rebuilt, and is marked as one replaceable image layer with no internal editability claim.
- additionally, its source must be the complete locked reference at the original pixel dimensions, with no pre-cleaning crop; reject any smaller hero derivative that omits regions of the locked reference.
- for every composite widget, the target readback must preserve the confirmed child boundaries: independently replaceable image children are image layers, text remains text, controls remain separate nodes, and icons are not replaced by vectorized artwork or parent-level image summaries. When a `参考保真视觉底图` was confirmed, its visual subject and dependent effects must remain one bottom image layer rather than being re-expanded into separate image or code layers.
- compare target readback against the internal UI IR-to-target traceability manifest: every required IR node must have a target node or explicitly reported fallback, presentation-row coverage must remain complete, and repeated counts must match exactly. A transport-level “success” without this node-level evidence is not complete.
- compare the delivered output against the latest table revision, not an earlier decomposition; any user-edited row that remains unchanged in UI IR or target output is a completeness failure;
- compare every target adapter's node and asset mapping against the canonical revision; target-specific conversion is acceptable, but changing `renderType`, dropping children, or failing to register a derived asset is a completeness failure;
- verify resolution normalization: requested, source, and target dimensions are real; declared aspect ratios exactly match pixel dimensions; source and target ratios are identical; `scaleX` and `scaleY` equal the ratios derived from those dimensions; no crop, stretch, padding, or inconsistent source-space geometry was introduced.

Do not depend on the user selecting a node when the adapter returned an identifier. Do not repeat local file searches after the write; the preflight and target readback are the evidence for the fast path.

## Verification modes

### Fast (default)

Use deterministic validation, one primary write, one inspected browser/target screenshot, and— for uniform-scale HTML—one reduced-width screenshot state. Record `verification.visual.status: "inspected"` and an evidence reference. Do not mark completion without this evidence. Reuse an existing browser page when possible; do not repeatedly start temporary servers or rerun the full contract scan after a screenshot-only update.

### Visual (deeper review)

Use the fast evidence plus a closer review of the visual subject/base, major containers, asset fit, typography hierarchy, and icon quality. Do not start a pixel-diff or multi-round repair loop by default.

For a static HTML preview, do not test interaction, animation, or product behavior. Inspect one representative browser screenshot. In `uniform-scale` mode, inspect the root and one reduced-width browser state to confirm text, images, cards, backgrounds, and every icon family scale from the same root context rather than reflowing independently. When explicit preview-only Zoom is enabled, inspect one changed Zoom state and the reset state; do not treat it as product interaction testing.

The deterministic validator does not decide whether a bitmap was visually cleaned well, whether a generated replacement preserves the reference, or whether two different-looking marks share the same meaning. Check those against the locked reference. If local image cleanup is uncertain, use the same-size clean-asset regeneration path rather than claiming an automated pass.

## Completion states

- `complete`: primary write succeeded and basic checks passed;
- `complete-with-known-difference`: primary write succeeded but a visible, non-critical difference is recorded;
- `submitted-unverified`: the target acknowledged the write but did not provide enough readback;
- `blocked`: the target could not create the requested editable structure.

Never call a transport acknowledgement alone `complete`. Do not block completion on minor spacing, anti-aliasing, or optical differences.

## Repair boundary

Make at most one focused repair for an obvious omission, unsupported icon, missing image fill, or clearly broken major region. A repair must create a new provisional revision and preserve the old revision, hash, and screenshot. Ask the user before changing meaning, text, reference-anchor assets, confirmed layout, scaling anchors, or product scope. Reject the repair and keep the prior revision if the new screenshot shows a meaningful change in root proportion, image ratio, text wrapping/overflow, main control placement, icon size, bottom navigation geometry, or composite-control alignment. If the repair is not unambiguous or does not work, report the difference and stop.

### HTML revision states

- `provisional`: HTML exists but has not completed contract and visual checks;
- `provisional / 校验未通过`: the revision is retained for diagnosis but is not delivered;
- `complete`: contract validation and visual-anchor inspection both pass;
- `complete-with-known-difference`: a non-critical, explicitly recorded visual difference remains;
- `blocked`: completion would require changing confirmed semantics or major visual anchors.

The validator is read-only and is a delivery gate, not an HTML/CSS generator. Its CLI diagnostics classify failures as `canonical-ir`, `html-contract`, `asset`, or `visual`; use that category to choose the next action. Do not rewrite HTML, CSS, UI IR, or assets merely to turn every message into `PASS`.
