---
name: image-to-ui
description: Turn an AI-generated UI image plus a user brief into an editable, source-level UI reconstruction. First lock the visual reference, then present a child-level decomposition together with a synchronized draft platform-neutral UI model for user review; after decomposition confirmation, emit the finalized structure to MasterGo, Figma, or another canvas with target-specific adapters and verification. Use for AI-image-to-canvas, screenshot-to-editable-UI, visual reverse engineering, and editable design-source generation.
---

# Image to UI

The input is a visual UI reference and a user brief. The brief has priority for product intent, content, and meaning; the image has priority for visible appearance, spatial relationships, and visual detail unless the user says otherwise.

The job is not to improve, restyle, or regenerate the reference. The job is to recover a plausible editable source file from it.

## Core workflow

1. Classify the input reference before visual-reference generation. Treat hand sketches, wireframes, low-fidelity mockups, annotated layouts, placeholder-heavy diagrams, and text-only briefs as visual-style sparse. For those inputs, read and silently apply [references/visual-completion.md](references/visual-completion.md) when calling `imagegen` to create the visual UI reference. Treat a finished UI screenshot, high-fidelity mockup, photograph, or other reference with clear, intentional visual styling as visual-style rich; do not load or apply the module for those inputs. If classification is ambiguous, preserve the supplied reference rather than applying style completion unless the user explicitly asks for visual refinement.
2. The visual-completion module applies only while generating the single locked visual reference. It may complete styling and non-semantic supporting detail within the user's product intent and the source's structural anchors, but it must not alter user-provided text, add unrelated product functions, or change the later decomposition, canonical UI IR, HTML, or canvas rules.
3. If the user starts from a sketch or only a brief, optionally call `imagegen` to create the visual UI reference. The sketch is input to image generation, not the source for the editable decomposition.
4. Lock the single final UI image as the reference artifact and ask for the user's opinion. Before presenting this confirmation, read [references/confirmation-controls.md](references/confirmation-controls.md) and always offer its visual-reference actions as complete plain-text choices. In Codex when the active `visualize` skill is available, also follow that reference's required compact in-conversation control-panel procedure and emit its inline-visualization directive; this panel is an acceleration path, never the only path. Do not decompose until the user confirms the visual reference. Preserve the complete, uncropped source image at its original pixel dimensions and record those dimensions before any asset extraction. Keep four objects distinct throughout the task: the immutable locked reference image; the cleaned full-canvas `参考保真视觉底图`; bounded independent image assets; and editable HTML/canvas nodes. Never use a cropped derivative as the visual-base source. Any regenerated, restyled, or materially edited UI image becomes a new locked reference and invalidates the previous decomposition.
5. After the visual reference is confirmed, prepare the complete child-level decomposition and a synchronized draft `ui-ir.json` together. Present the decomposition using the fixed user-facing format in [references/decomposition.md](references/decomposition.md): Screen metadata followed by one five-column table per named component. Keep the format stable and do not expose internal tree fields by default. Generate the draft IR directly from the presented tables in the same revision: its `presentationRows` must be an exact machine-readable copy of the tables, and every additional IR node must be an explicit structural child of one or more presented rows without changing their count, meaning, implementation route, or editable result. Save the draft beside the requested output location with status `awaiting-user-confirmation`; it is not eligible for HTML or canvas generation.
6. Ask for one decomposition review. If the user requests a change, update the affected table row first, then synchronously update the draft `ui-ir.json`, its presentation-row-to-node mapping, asset records, and target mappings in a new revision. Re-present the changed table content and the synchronized draft status. Do not continue while the table and IR differ. When the user confirms the decomposition, finalize the same canonical UI IR and asset package for the locked reference revision. Build the IR as an unlimited-depth tree with explicit `id`, `parentId`, `children`, `order`, `bounds`, `role`, `renderType`, `assetAction`, and platform-neutral `targetKind`. Put platform-specific kinds and routes under each node's `targets.<adapter>` mapping. Use `renderType` for representation (`code`, `vector-asset`, `raster-asset`, or `mixed`) and use `provenance` for origin (`source`, `imagegen`, `generated-svg`, `cleaned-reference`, `local-library`, or `code-authored`). Every `raster-asset` or `vector-asset` node must have a non-null `assetId`; code-authored inline SVG is `code`, while an inlined library/generated SVG remains a `vector-asset` mapped to its source `assetId`. For every raster asset node, record `assetId`, `assetPath`, pixel dimensions, alpha/transparency status, `sourceCrop`, `fitMode`, provenance, and `assetAction`. For every locally resolved Lucide icon, record `assetId: "lucide:<resolved-name>"`, `assetAction: "resolve-icon"`, and `provenance: "local-library"`. Read [references/fidelity.md](references/fidelity.md) before this conversion. Target adapters may add target-specific mappings or derived import formats, but every new asset must be registered in the canonical package with `derivedFrom` when applicable before the target is marked complete. Block any delivery until every declared image asset exists at its saved path and the generated HTML or canvas actually references the corresponding asset.
7. After presenting the decomposition and synchronized draft, read [references/confirmation-controls.md](references/confirmation-controls.md) and always offer its four decomposition-confirmation/output actions as complete plain-text choices. In Codex when the active `visualize` skill is available, also follow that reference's required compact in-conversation control-panel procedure and emit its inline-visualization directive. A previously named target is a suggested default only; an explicit current choice overrides it. Do not make HTML a default approval gate.
8. Select the requested canvas adapter. For MasterGo, use the active `mastergo-mcp` skill and its native MCP workflow. If MasterGo is requested without a specified design source, default to `free-draw`; do not ask the user to choose a mode. Do not duplicate MasterGo tool instructions here. Keep Figma and future platforms behind the same adapter boundary.
9. Before writing, communicate with the target service and inspect its actual available resources, supported icon/component/vector routes, image requirements, and relevant tool operations. Treat a target-native resource as usable only when the service exposes a concrete resource/component route and the written result can be read back as the expected node type. Do not assume that an SVG file or inline SVG becomes a native editable vector. Resolve mappings before generation. Never use generic keyword placeholders for confirmed visual assets.
10. Generate target-specific canvas source from the latest canonical UI IR and local asset package, not by submitting the browser-preview HTML unchanged. A self-contained preview may contain data URLs and browser-only CSS; the canvas adapter must emit only representations the target preflight confirmed. Submit through the selected adapter in one primary pass. Do not hard-code a platform's exact tool sequence here; follow the active target skill.
11. Use the adapter's returned root or target identifier for one lightweight structural readback: root existence, major node/element counts, text, icon/image presence, and obvious structural failures. Do not turn routine work into a pixel-diff or multi-pass loop.
12. Automatically correct only clear failures when the correction is unambiguous. Ask before changing meaning, replacing a reference-anchor asset, or making a material design decision.
13. Report the result and any unresolved differences. Do not claim completion when the target service did not provide enough readback to verify basic completeness.

The local HTML preview is optional and static. If selected, save `ui-ir.json` and all independent image assets under the output directory before generating `index.html`. The delivered HTML is a hard self-contained artifact: inline CSS; use locally resolved inline SVG for icons; embed every raster asset as a data URL derived byte-for-byte from its canonical file. Any external URL or relative/local resource reference blocks delivery. Keep canonical files and `assetPath` records for traceability and canvas adapters. Mark every rendered UI node with a unique `data-node-id`; mark every raster or vector asset-bearing element with its canonical `data-asset-id`. For a Lucide icon, also set `data-icon-source="lucide:<resolved-name>"`. Do not add visible text through unmapped HTML or CSS pseudo-content.

For the default `targets.html.layoutMode: "uniform-scale"`, keep one fixed-aspect-ratio root design canvas and derive child geometry from normalized UI IR bounds. The root element must declare `data-ui-root`, `data-design-width`, and `data-design-height`, establish its own CSS container-query context, and use a literal `aspect-ratio` exactly matching `targetDimensions`. Never combine `width: 100%` and `height: 100%` on that root; this defeats the ratio constraint. Scale typography, spacing, and control sizes with root container units or equivalent normalized design-space values. Viewport units may size the page shell or one root-canvas axis so the fixed-ratio canvas fits the browser, but they must not size descendant UI nodes or independently set both root axes. Do not use `clamp()` minima, non-zero fixed `min-width`/`min-height`, or media-query reflow inside this mode. Use `min-width: 0`, `min-height: 0`, and bounded overflow where needed. Use a separate explicitly confirmed `reflow` mode only when the decomposition calls for rearrangement rather than proportional scaling. Do not use `overflow: visible`, z-index, clipping, or masks to conceal a failed layout or duplicate content. Read [references/icon-assets.md](references/icon-assets.md) and run the bundled resolver with `--inline` for every icon that it can match; inline SVG is the output form, while Lucide is the recorded source. Do not hand-author a replacement SVG when the resolver can supply the icon. Do not add JavaScript interactions, icon runtime libraries, click states, navigation, or animation.

For static HTML, use inline SVG markup for icons, preferring the bundled local Lucide cache. Read [references/icon-assets.md](references/icon-assets.md) and place every inline SVG inside an explicitly sized icon container in the root design-space units; apply `display:block`, `width:100%`, and `height:100%` to every inline SVG so source intrinsic dimensions never control rendered size. Do not use icon characters, Emoji, icon fonts, runtime CDN assets, or JavaScript-based icon loading. If an icon cannot be resolved, follow the fallback order in [references/icon-assets.md](references/icon-assets.md) and report a placeholder rather than hiding the failure.

When a confirmed HTML preview is later synchronized to a canvas, use the locked AI UI image and confirmed UI IR as the primary visual and structural references. Merge changes the user explicitly made to the HTML, but do not promote an HTML screenshot to the sole visual source automatically.

Use the same canonical `ui-ir.json`, revision, and asset registry for HTML, MasterGo, and Figma outputs. A target-specific branch must read the latest canonical revision and write back any newly generated or converted asset registration and target mapping before reporting completion. Do not maintain a branch-local UI IR that can change `renderType`, omit children, or hide assets from other targets.

After writing an HTML preview but before validation, immediately report its path as `provisional` with the meaning “HTML 预览已生成，正在校验。” Continue the existing validation, screenshot, and visual-evidence workflow in the same task. Report a final delivered result only after the gate passes; if it fails, retain the path but label it `provisional / 校验未通过` and list the failures. Do not defer or skip the gate.

Run the bundled deterministic gate before delivery or canvas submission:

```bash
python3 "/absolute/path/to/image-to-ui/scripts/validate-delivery.py" --ir /absolute/output/ui-ir.json --html /absolute/output/index.html
python3 "/absolute/path/to/image-to-ui/scripts/validate-delivery.py" --ir /absolute/output/ui-ir.json --target mastergo
python3 "/absolute/path/to/image-to-ui/scripts/validate-delivery.py" --ir /absolute/output/ui-ir.json --html /absolute/output/index.html --require-visual --visual-evidence /absolute/output/preview-check.png
```

Resolve the script path from the directory containing this `SKILL.md`. Run the IR/HTML or target preflight first, then run the final form with `--require-visual` after inspecting at least one browser or target screenshot and recording it under `verification.visual`. A non-zero exit blocks completion. The script validates tree integrity, child-level presentation lineage, route locking, real asset files and metadata, exact data-URL bytes, mapped text/nodes, self-containment, root-canvas ratio, strict source/target normalization, Lucide metadata, target-mapping completeness, and the presence of visual evidence. It does not judge visual similarity or semantic image cleanliness; the agent must inspect the evidence against the locked reference and use the full-redraw fallback when local cleaning is uncertain.

## Decomposition is the approval gate

Read [references/decomposition.md](references/decomposition.md) before analyzing an image. Use its fixed Screen metadata block plus component-grouped five-column tables. Return the exact user-facing format defined there; JSON and structural lineage fields are internal only. The presentation covers:

- screen bounds and major regions;
- every visible text, control, repeated widget, icon, image, and meaningful decoration;
- visible count, semantic role, rendering route, editable result, and important fidelity notes;
- rendering route: `code`, `vector-asset`, `raster-asset`, or `mixed`;
- asset origin where relevant: `source`, `imagegen`, `generated-svg`, `cleaned-reference`, `local-library`, or `code-authored`;
- the user-readable implementation strategy and any fidelity-critical asset constraint;
- the concrete editable result expected from reconstruction;
- confidence-sensitive decisions and user-visible limitations.

For every composite component, list each independently editable or separately replaceable part as its own row. Use user-readable route labels such as `独立位图资产（AI生成）`, `独立 SVG 矢量资产`, or `代码绘制`; do not expose the ambiguous legacy label `generated-asset` to users. Do not create child rows for a visual subject, projection, reflection, lighting, atmosphere, or texture cluster that is intentionally kept together as one `参考保真视觉底图`; represent that cluster with one raster row and one IR node. A row may describe one small composite control when that is clearer, but it may not replace the child rows for independently editable controls. The canonical `presentationRows` must preserve these exact confirmed rows, counts, and implementation routes. The internal UI IR must split composite controls only where the children are genuinely independently editable; it must not split a visually dependent raster cluster merely for structural detail. Every IR node has exactly one `renderType`, one `assetAction`, one `assetId` or `null`, and one target representation. If the row-to-node mapping is incomplete or ambiguous, stop at decomposition confirmation.

The child-level list is not an internal convenience: show it to the user before confirmation. For repeated controls, list every semantically distinct instance or a repeat group with an exact count and explicit per-instance meanings. For a Dock, navigation bar, toolbar, or similar icon group, enumerate every icon separately. Keep concrete source IDs, target routes, expected node types, and fallback status in the internal manifest and surface only unresolved or fidelity-relevant details in `关键说明`. Missing icon rows or a generic “five icons” summary block confirmation and canvas generation.

Do not treat presentation hierarchy as the UI IR schema. Give every presentation row an internal stable `presentationRowId`, then map it to one or more explicit UI IR node IDs. Derive depth from `parentId`; do not impose a three-level limit. Preserve component membership, order, count, meaning, rendering route, asset action, and editable target across the mapping. Never flatten a repeated item, composite control, image-bearing region, or other independently editable child merely because the user-facing row is concise. The exception is an intentionally unsplit `参考保真视觉底图`: its visually dependent internal content must remain one raster node and must not be re-expanded into nominal child assets.

When the user changes a table item in conversation, create a synchronized revision before generating output. Resolve the change to its `presentationRowId`, update all mapped UI IR nodes and their `parentId`/`children` relationships, update or regenerate affected assets, and update the HTML/canvas target mapping. Record the change in a machine-readable `changes` list with `before`, `after`, and affected node/asset IDs. A table revision without a corresponding UI IR revision is invalid.

The draft `ui-ir.json` is generated together with the first presented decomposition so table-to-IR consistency can be reviewed early, but it must remain `awaiting-user-confirmation` and must not be used for HTML or canvas generation. Do not proceed to canvas or HTML generation until the user confirms the decomposition and selects or confirms the output target. Any correction must update the table and draft IR in the same revision before the next confirmation.

## Brief and image precedence

- The user's one-line brief is the highest-priority authority for product intent, requested content, labels, and meaning.
- After image generation, the final generated image is the visual source of truth for visible elements, layout, style, and counts.
- Preserve visible image details that do not conflict with the brief.
- If the image contains illegible or hallucinated text that conflicts with the brief, use the brief and record the image discrepancy.
- Do not add fields, actions, destinations, metrics, or workflows merely because they are conventional.
- Do not preserve an obvious image-generation artifact when the brief gives a clear intended meaning.
- Do not allow later asset generation, platform constraints, or convenience placeholders to silently change the locked reference's major visual anchors.

## Source-level reconstruction rules

### Reference-fidelity visual base

When the locked reference contains a UI visual subject whose projection, reflection, lighting, background atmosphere, texture, or spatial relationship would materially drift if separated, use the exact term `参考保真视觉底图` (`reference-fidelity visual base`). Unless the user explicitly requests independently editable parts and suitable clean assets can actually be produced, preserve the visual subject and all visually dependent effects together in this one cleaned full-canvas raster layer. Do not mechanically split the subject, its dependent effects, and its surrounding atmosphere into separate layers. Text, cards, buttons, icons, controls, and other confirmed editable UI remain independent above it.

The source for this operation is the complete locked UI image, not a previously extracted hero image or slot crop. If the only available asset is already cropped or reduced from the locked image, stop and report the missing full-resolution source; do not upscale, recrop, or infer the omitted canvas regions.

Follow this sequence:

```text
locked AI UI reference
→ identify and remove text, buttons, icons, cards, and controls that will be rebuilt
→ repair the background regions exposed by their removal
→ retain the UI visual subject and its dependent projection, reflection, lighting, atmosphere, texture, and spatial relationships
→ generate or clean the base to the canvas's exact width, height, and aspect ratio
→ place it as the bottom-most image layer at 100% width and 100% height
→ rebuild editable controls above it
```

The base must never be the original full UI screenshot with controls still present, and it must never be made from a pre-cropped derivative. It is allowed to be a cleaned visual scene that fills the canvas, but the resulting text, cards, buttons, icons, and controls remain independent editable nodes above it. Treat the cleaned image itself as one replaceable image layer; do not claim that its internal visual content remains separately editable. `Edge-to-edge` means exact-size placement, not stretching: clean the complete source to the locked canvas dimensions and aspect ratio, then place the result without distortion, crop, or gap.

- Rebuild layout, containers, widgets, text, and independently editable simple effects as editable nodes. Effects that are visually dependent on a reference-fidelity visual base remain inside that single raster layer.
- Use external vector assets for icons, logos, and illustrations that are genuinely vector-like or available from an authoritative library.
- Use independent raster assets for isolated image regions whose boundaries and visual dependencies are clear, such as an independent cover, texture, or illustration. Keep a visually dependent subject/effects cluster in the cleaned full-canvas `参考保真视觉底图` instead of creating several nominally independent raster assets.
- Use image generation only for an identified asset region that needs it; never generate a replacement full-screen UI just to guide reconstruction.
- Split mixed layers only when the resulting children can remain independently editable without material visual drift. A `mixed` label is only valid for a parent whose independently editable children are explicitly identified; a visually dependent subject/effects cluster is intentionally one raster child and is not split into nominal image, light, shadow, or texture layers.
- Treat the decomposition as an asset-boundary checklist, not just a visual summary. For every composite widget, inventory the frame/container, text, independently replaceable images, icons, controls, and meaningful editable effects. When the visual subject and its dependent projection, reflection, lighting, atmosphere, or texture are kept together, record them as one `参考保真视觉底图` row/node rather than listing each internal visual ingredient as a separate child.
- When extracting an image asset from a reference that contains UI, distinguish the complete reference image, the `参考保真视觉底图`, the independent image region, and UI content embedded inside the image. Never directly crop and reuse a region that still contains text, icons, controls, markers, decorations, or other content that will be rebuilt as independent nodes.
- Before using such an image asset, create a removal mask for the UI content that will be rebuilt. Use local cleaning or local redraw only when the removal boundary and repair operation are clear. If they are uncertain, generate a clean independent image at the target asset's exact dimensions and aspect ratio instead. Full redraw means the image asset only, never a replacement full-screen UI. Record the removed content, retained content, source crop, `assetAction`, `provenance`, `fitMode`, dimensions, transparency, and internal editability accurately.
- Keep every independently replaceable image region as its own asset only when separating it does not break a visually dependent UI subject. By default, merge the UI visual subject with its dependent projection, reflection, lighting, background atmosphere, and texture into the cleaned full-canvas `参考保真视觉底图`. Split such content only when the user requests it and a real clean independent asset is available. Record retained visual content, removed UI content, and `internalEditability: false`.
- Materialize every image-bearing node before producing HTML or a canvas handoff. Save the file, record its relative `assetPath`, stable `assetId`, pixel `width` and `height`, `hasAlpha`/transparency status, `sourceCrop`, intended `fitMode`, and `provenance` in `ui-ir.json`. A declared `raster-asset` without a file at that path is an unresolved blocker.
- Treat generation as provenance, not representation: an AI-generated PNG/WebP is `renderType: raster-asset` with `provenance: imagegen`; an independently saved generated SVG is `renderType: vector-asset` with `provenance: generated-svg`; an inline SVG or CSS shape authored inside HTML is `renderType: code` with `assetAction: code-render`. Legacy `generated-asset` is input-only compatibility: normalize it to `raster-asset`, resolve provenance and file format, record the migration in `changes`, and never emit it in new tables or manifests. See [references/decomposition.md](references/decomposition.md).
- Never use Unicode characters, text nodes, Emoji, glyphs, or icon fonts to draw non-semantic visual primitives. This includes avatar eyes, mouths, dots, decorative marks, icons, arrows, and geometric markers. Use an independently addressable shape/vector/path node or a verified vector asset instead. Text nodes are reserved for actual readable copy and must not be used as a visual-pixel substitute.
- For any foreground visual declared as an independently editable cutout, record whether the asset actually has transparency. Do not simulate extraction by placing the complete UI screenshot in a rectangular CSS background and changing `background-position`; produce an alpha-bearing asset or explicitly report that the independent cutout is unavailable.
- For a complex visual scene, follow the dedicated `参考保真视觉底图` procedure above. Start from the complete locked source at its original dimensions; do not crop to a local slot first. Remove visible text, buttons, icons, cards, and controls; repair the exposed background; retain the UI visual subject and all visually dependent effects; and keep the cleaned result as one replaceable image layer with no claim of internal editability.
- Plan every image-bearing node together with its destination slot. An illustration or other image asset should fill its specified slot by default. When source and slot aspect ratios conflict, first clean the asset, extend or repair its background/edges, or generate the region at the slot ratio; do not solve the conflict by silently cropping away the subject, leaving accidental gaps, or stretching the image. Record an intentional `fitMode` such as `contain`, `cover`, `stretch`, or `overlay` when the design calls for it.
- Before HTML or canvas generation, compare the visible content represented inside each image asset with the independent UI nodes that will be placed above it. If the same semantic element appears in both, clean the asset, remove the duplicate node, or explicitly preserve it as an inseparable image composite. Do not hide duplication with z-index, opacity, masks, or clipping. If the asset boundary cannot be resolved, do not generate from the ambiguous asset.
- Do not claim an icon is a native editable vector merely because its source is SVG. Native editability is a target capability that must be established through MCP/resource inspection and one successful readback.
- Preserve exact visible counts. A canvas result with missing or extra controls is a failed result.

## Platform-neutral model

The decomposition manifest is the source of truth. It must not contain platform-specific assumptions in its semantic core. Each node may have adapter mappings such as:

```json
{
  "id": "node-021",
  "role": "button",
  "bounds": {"x": 840, "y": 64, "width": 120, "height": 40},
  "content": {"text": "Play"},
  "renderType": "mixed",
  "style": {"fill": "#111827", "radius": 20},
  "children": ["container-021", "icon-021", "text-021", "illustration-021"],
  "targets": {
    "mastergo": {"kind": "frame"},
    "figma": {"kind": "frame"}
  },
  "confidence": "confirmed"
}
```

Adapters translate this model into supported native structures. They must not flatten the screen, silently drop unsupported children, or claim success from transport acknowledgement alone.

## Canvas generation and verification

Read [references/canvas-generation.md](references/canvas-generation.md) and [references/verification.md](references/verification.md) when entering those phases.

Verification is driven by the decomposition manifest, not by whether the canvas tool returned `success`. Keep it lightweight and completion-oriented:

- structure: node IDs, parentage, order, type, text, and repeated counts;
- geometry: screen bounds, major regions, alignment, spacing, and size;
- appearance: fills, borders, radii, shadows, typography roles, icon weight, and image crops;
- representation: semantic text remains text; non-semantic visual primitives remain shape/vector/path nodes or verified vector assets, never text glyphs;
- assets: identity, source path, resolution, alpha, and independent editability;
- completeness: no missing or invented meaningful elements.

Before writing, resolve target resources and supported representations so that predictable failures are prevented in the primary pass. After writing, check only the high-value invariants: root exists, meaningful node counts match, text is present, icons and images are not missing placeholders, and the main hierarchy is intact. Use the returned root or target identifier for one structural readback when supported. Do not repeat local file searches or rescan the project after a successful write. Use the smallest correction for an unambiguous failure; do not launch a long pixel-diff or repair loop for routine work.

Before HTML or canvas generation, run the bundled `validate-delivery.py` resolved relative to this skill directory against the canonical UI IR. For canvas generation, pass `--target <adapter>` after adding every node's `targets.<adapter>` mapping. For HTML, run it again with `--html` after writing the self-contained preview. Do not report completion or submit to a canvas while the validator exits non-zero.

Also compare the decomposition checklist with the UI IR as a visual/semantic lineage audit: every presentation row must map to one or more existing IR nodes, every required IR node must be covered by a presentation row, every image-bearing child must still be an image asset, every icon-bearing child must still be a vector route or explicitly reported fallback, and no concise presentation row may replace required child-level mappings.

For HTML and canvas generation, extend this lineage audit to confirm that every composite component's visible children remain within its intended bounds under the selected scaling context, that every image asset's cleaned content boundary matches the decomposition, that no image asset duplicates an independent UI node, and that `provenance`, `assetAction`, `assetPath`, dimensions, transparency, and actual file content agree. Resolve any mismatch before writing; do not use layering or clipping as a substitute for resolving it.

For a canvas target, full traceability is a mandatory internal preflight artifact. It must cover every UI IR text, image, texture, icon, control, repeated item, and meaningful effect. Do not write to MasterGo until every IR node has a target mapping and expected node type; if the target route is unresolved, preserve the slot and report the blocker instead of dropping the node. Show the full mapping to the user only on request; otherwise report readiness, fallbacks, and differences concisely.

## Resolution and coordinate normalization

Never treat a historical task size or reference-image size as a default output size. Record the user's requested output separately from the actual image-generation result and the target canvas:

```json
{
  "requestedCanvas": {"width": 1920, "height": 1080, "aspectRatio": "16:9"},
  "sourceDimensions": {"width": 1536, "height": 864, "aspectRatio": "16:9"},
  "targetDimensions": {"width": 1920, "height": 1080, "aspectRatio": "16:9"},
  "normalization": {"mode": "uniform-scale", "scaleX": 1.25, "scaleY": 1.25, "crop": false, "stretch": false}
}
```

If the generator cannot produce the requested dimensions but produces the exact same aspect ratio, scale the complete source and all UI geometry uniformly to the requested target. Compute `scaleX` and `scaleY` from the real dimensions and require them to be equal. A declared ratio such as `16:9` is valid only when the pixel dimensions satisfy it exactly. If the aspect ratios differ, regenerate or repair to the exact ratio before delivery; otherwise block. Do not crop, stretch, pad, or silently falsify the scale values. Apply the same transform to the visual base, every UI IR bound, font/icon size, spacing, and target placement.

Use two verification modes:

- `fast`: deterministic validation, one primary write, one structural readback, and one inspected browser/target screenshot. This is the default completion path.
- `visual`: the fast mode plus a closer review of visual anchors, asset fit, typography hierarchy, and icon quality; do not turn it into a pixel-diff loop.

## Output

At the decomposition stage, return the Screen metadata and fixed decomposition table for confirmation, and save a synchronized draft `ui-ir.json` with `status: "awaiting-user-confirmation"`. Every newly generated or materially revised reference image must be accompanied by a fresh complete table and a fresh draft IR revision. After decomposition confirmation and target selection, finalize and produce:

- the decomposition / UI-IR manifest;
- the saved `ui-ir.json` path and complete local asset package, including representation and provenance for every asset;
- the internal presentation-row-to-UI-IR-to-target traceability mapping, with a concise user-visible readiness/fallback summary for canvas outputs;
- local independent assets and their provenance;
- the selected canvas adapter output;
- a short completion or unresolved-issues report;
- optional self-contained `index.html`; create a separate `styles.css` only when the user explicitly requests a non-self-contained project output.

Do not create more than one visual UI reference or require a second visual-direction approval unless the user explicitly asks for design exploration. The generated UI image and its decomposition are the single confirmation package.

## Scope boundaries

This skill reconstructs visual UI source structure. It does not implement product behavior by default.

Do not add or test:

- click handlers, navigation, playback, form submission, or state transitions;
- JavaScript, animation, hover effects, or simulated data updates, except the explicitly requested preview-only root-canvas Zoom described in [references/icon-assets.md](references/icon-assets.md);
- product behavior or separate design variants; responsive page-shell fitting is allowed for local HTML previews, but descendant UI nodes in `uniform-scale` mode must remain in the fixed design space and scale with the root rather than reflow independently;
- interaction testing or repeated browser automation; one browser/target screenshot inspection is required for visual completion, and a temporary local static server is allowed only when necessary to make the self-contained HTML observable;
- pixel-perfect comparison, exhaustive asset forensics, or iterative visual optimization.

Only add these when the user explicitly requests them.
