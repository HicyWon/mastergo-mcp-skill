# Canvas Generation

This reference defines the platform-neutral handoff contract. Platform-specific tool usage belongs to the active target skill.

## Before writing

- Load the confirmed decomposition manifest.
- Materialize the confirmed UI IR as `ui-ir.json` before writing. Do not proceed with an IR that exists only in internal reasoning.
- Resolve the validator relative to the active image-to-ui skill directory, then run `python3 "/absolute/path/to/image-to-ui/scripts/validate-delivery.py" --ir /absolute/output/ui-ir.json --target <adapter>` before the primary canvas write. A non-zero exit blocks submission.
- Confirm that the latest conversational table revision is reflected in `ui-ir.json`, its `changes` list, all affected asset records, and target mappings. A stale table-to-IR revision blocks writing.
- Confirm that this target uses the canonical `ui-ir.json` and asset registry for the locked reference revision. Target-specific mappings may be added under the target adapter, but a branch-local manifest or unregistered derived asset blocks completion.
- Confirm that the manifest version/hash belongs to the currently locked reference image and was derived from the fixed Screen metadata plus component-grouped five-column tables. If the image was regenerated or materially edited after confirmation, stop and produce a new complete decomposition before writing.
- Ensure every independent asset exists at a stable local path.
- For every image asset node, verify `renderType`, `provenance`, `assetId`, `assetPath`, `width`, `height`, `hasAlpha`, `sourceCrop`, and `fitMode`; reject any missing field or missing file. Normalize legacy `generated-asset` inputs according to the migration rule in [decomposition.md](decomposition.md) before target mapping.
- If the target adapter creates or converts an asset, register it in the canonical asset package with its source `assetId`, `derivedFrom`, format, dimensions, alpha status, and target mapping before writing the completion state.
- Resolve every node to a target representation or record an explicit fallback.
- Preserve node IDs, parentage, order, bounds, text, counts, and semantic roles.
- Preserve representation semantics: readable copy is a text node; non-semantic visual primitives such as avatar facial features, dots, arrows, decorative marks, and geometric markers must be shape/vector/path nodes or verified vector assets, never text glyphs or icon characters. The target readback must reject a text node where the IR expects a non-text visual node.
- Generate the canvas from the internal UI IR tree, never directly from the simplified user-facing tables. Preserve unlimited-depth `parentId`/`children` structure, node order, bounds, text, counts, roles, and render routes. Use the internal `presentationRowId → nodeIds` mapping for lineage; do not require one table row to equal one IR node and do not collapse composite controls into one route.
- Use the UI IR target coordinate system, not a historical reference size. Record `requestedCanvas`, `sourceDimensions`, `targetDimensions`, and `normalization` before writing. When aspect ratios match, apply one uniform transform to all image bounds and UI geometry; never scale the background independently from controls.
- Translate unsupported features into the closest editable target structure; never silently flatten them.
- Inspect the target service's available icon, component, variable, image, and import routes before generating code. Prefer a verified target resource over guessing a library name or icon identifier.
- Build a compact mapping table for icons and other reference-anchor resources before the primary write. For each icon record `iconMeaning`, exact target match, normalized aliases, chosen source, target route, expected node type, and verification status. Do this only after communicating with the target MCP; do not infer resource availability from a skill description or an HTML convention.
- For MasterGo, keep the canonical icon semantic and Lucide source unchanged, but record the actual target fallback under the same node's `targets.mastergo`, for example `{"kind":"image/vector","expectedNodeType":"image","iconFallback":"fas fa-phone","verified":true}`. A source SVG or Lucide record is not evidence that MasterGo can render it natively. Follow the active `mastergo-mcp` skill's conservative FontAwesome candidate set, root readback, duplicate-placeholder detection, screenshot confirmation, and `agent_replace_node` repair rule.
- Build the full canvas traceability manifest from UI IR nodes, not from component headings or concise presentation rows. Include every node ID, its presentation-row mapping, target route, expected node type, and verification status. For repeated controls or icons, include each instance and exact count. Any missing confirmed repeated child is a preflight failure.
- Use the locked reference and confirmed fidelity tiers when choosing between source extraction, code rendering, and generated regions.
- When the manifest uses `参考保真视觉底图`, verify before writing that it keeps the UI visual subject together with its visually dependent projection, reflection, lighting, background atmosphere, and texture by default; that all rebuilt UI was removed and repaired; and that the asset is exact-canvas size, `internalEditability: false`, bottom-most, and placed without stretching.
- For that route, verify that the source bounds equal the complete locked reference bounds and that no crop or `object-fit: cover` occurred before cleaning. A smaller hero derivative cannot be accepted when it omits regions of the complete locked reference; recover the complete source instead.
- If a user-confirmed HTML preview is being synchronized to a canvas, use the locked AI UI reference and UI IR as the primary sources, then merge explicit user edits from the HTML. Generate separate adapter source from the UI IR and canonical local assets; do not submit the self-contained preview unchanged because its data URLs and browser CSS are not evidence of target support. Treat an HTML screenshot as a secondary comparison surface, not as an automatic replacement reference.
- Before writing, reject any UI IR node whose implementation is a combined summary such as `raster-asset + code + vector-asset`; combinations are allowed only in a user-facing presentation row and must resolve to separate child nodes in UI IR. Image-bearing children must remain raster assets, not vector drawings. A generated SVG is a vector asset only when it exists as a standalone SVG file; an inline SVG remains code-rendered.
- For HTML output, verify every image-bearing UI IR node against its declared `assetId`/`assetPath` and confirm that the embedded `img src` or CSS `url(...)` data URL is derived from that exact local asset with matching dimensions, transparency, and content. A local path may be used only when explicitly requested or when the target adapter requires it. Do not let multiple unrelated nodes silently reuse the complete UI reference image. A missing, mismatched, or untraceable asset blocks delivery.
- Do not submit until every required UI IR node has a target mapping and every presentation row is covered by one or more mapped nodes. If a target icon route is unresolved, keep the slot as an explicit fallback and report it; never silently omit the icon.
- Resolve the root node returned by the target write and use that ID for the one planned readback. Do not depend on a user selecting the node when an ID is available.

## Adapter contract

Each adapter should expose the smallest useful set of conceptual operations:

1. `prepare(manifest, assets)`
2. `create_or_update(root)`
3. `readback(root)`

The MasterGo adapter must follow the active `mastergo-mcp` skill. A future Figma adapter should follow the active Figma integration. The image-to-ui skill owns the semantic manifest and verification expectations, not the platform API details or exact tool sequence.

## Generation rules

- Prefer native editable frames, text, vectors, components, and image fills.
- Use a single root frame and stable IDs where the target supports them.
- Keep image regions independent from surrounding widgets.
- Keep icons independent from text and containers.
- Keep visual primitives independent from semantic text. Do not implement eyes, mouths, dots, arrows, or decorative geometry with text characters, Emoji, glyphs, or icon-font output.
- Keep each independently editable composite-component child addressable in the target tree. Image-bearing children must remain image fills/assets; only surrounding structure, text, controls, simple geometry, and verified icons may use code/vector routes. A deliberately unsplit `参考保真视觉底图` remains one image child; do not manufacture child layers for its internal visual subject, light, shadow, or texture.
- Keep repeated widgets structurally repeated rather than duplicating a flattened image.
- Use the original image only as a comparison reference, never as a visible fallback layer.
- A `参考保真视觉底图` is the one allowed full-canvas visual scene layer. It must be cleaned, never the complete UI screenshot. Keep the UI visual subject and its dependent effects together unless the user requested a split and real clean independent assets exist. Recreate text, cards, buttons, icons, controls, and other confirmed editable UI as independent nodes above it.
- Do not create a smaller hero container and place the visual base inside it. The bottom visual-base node must match the root canvas width and height; do not emit `object-fit: cover` or any other crop behavior for this node.
- For a requested target such as `1920 × 1080`, a same-ratio generated source may be uniformly scaled to that target. The adapter must receive target-space bounds for every node and must not retain source-space pixel sizes for controls, text, icons, or images.
- Resolve icons in this order: (1) a concrete target-native resource/component exposed by the MCP and confirmed by readback; (2) the bundled Lucide cache through a target-supported vector route; (3) a version-pinned local Material Symbols asset through a verified target route; (4) a deterministic vector drawing from basic primitives; (5) a circular placeholder only for a non-critical icon, marked `placeholder`, excluded from visual-completion claims, and reported. An SVG file, inline SVG, icon-font class, or library name is not evidence that the target will create an editable vector node. Do not knowingly emit an unsupported identifier or generic keyword image. For critical icons, preserve the slot and report the unresolved difference instead of silently substituting.
- For MasterGo pages with two or more semantic icons, do not accept a circular placeholder route. Treat distinct semantic icon nodes that read back to the same `./asset/icons/svg_*.svg` as a failed target mapping, replace the affected node with a verified fallback, and re-read the root before reporting completion.
- For online libraries, semantic similarity is only a candidate-selection aid. Verify meaning, stroke/fill style, viewBox, license/source, target import route, and actual target node type before batch use. If the MCP exposes no verifiable native/vector route, treat the library asset as an unverified external image/vector-like asset, not as a native icon resource.
- Read back once after the primary write when the target service supports it. If basic structure is clearly broken, make one focused repair attempt; otherwise report the result and continue.
- Prefer the identifier returned by the primary write over selection-based lookup.
- Do not run repeated local `find`, `rg`, or project-directory scans after a successful write. Verify prepared assets before submission and inspect the returned target structure once.

The primary generation pass is the priority. Do not add speculative multi-pass optimization, pixel-perfect comparison, or exhaustive repair loops unless the user requests them or the first write exposes a material defect.

## Automatic repair boundary

At most one automatic repair pass is allowed for clear, non-semantic failures when the target service supports a reliable update path:

- omitted or duplicated nodes when the intended count is unambiguous;
- wrong order, parent, bounds, spacing, fill, radius, border, shadow, or typography setting;
- wrong icon placement or image crop when the source asset is already confirmed.

If a target icon or component cannot be resolved during preflight, use a verified equivalent or record the fallback before writing. Do not knowingly emit an unsupported icon identifier and wait for a placeholder to appear. Do not keep iterating after the first repair fails; report the limitation.

Ask the user before:

- replacing a reference-anchor asset;
- changing text or product meaning;
- inventing a missing interaction or content field;
- selecting a materially different icon or illustration;
- accepting a platform limitation that visibly changes the design.

The in-app browser is an optional visual observation surface only. It may be used to open a user-accessible canvas page or inspect a screenshot when explicitly requested, but it does not replace the target MCP's write/readback path. A page visible in the in-app browser does not prove that the MasterGo MCP is connected to the same document.

## Verification mode

The default adapter path is:

```text
prepare → primary write → root-id structural readback
```

Inspect one target screenshot before completion in both modes and record it as visual evidence. The deeper `visual` mode reviews that same evidence more closely; do not add repeated screenshots or structural dumps for routine work.
