# Reference Fidelity

The confirmed AI-generated UI image is the single visual source of truth. The goal is not to make the canvas merely plausible; it is to keep the first editable canvas pass visually close to the confirmed image without introducing a long repair loop.

## Lock the reference

Before decomposition, record one reference artifact:

- stable local path;
- viewport, original pixel width and height, and screen boundary;
- whether the locked source is complete and uncropped (`sourceCrop: none` before cleaning);
- selected image identifier or hash when available;
- brief version used to generate it.

The locked source image must remain available at its original pixel dimensions through the cleaning step. A viewport boundary is not permission to crop the source. If only a cropped local derivative or a resized preview is available, mark the task `blocked` for the visual-base path and request/recover the complete source; do not use the derivative as the base, upscale it, or claim full-canvas fidelity.

Do not silently switch to another generated image, a later regenerated asset, or a reconstructed HTML screenshot as the visual reference.

## Keep four objects distinct

Do not merge these concepts in reasoning, UI IR, filenames, or reporting:

| Object | Meaning | Delivery role |
|---|---|---|
| locked reference image | immutable complete visual source of truth | comparison and decomposition only; never visible delivery content |
| cleaned `参考保真视觉底图` | full-canvas raster derived from the locked reference after removing rebuilt UI | bottom-most replaceable image layer; internal visual subject/effects are not separately editable |
| independent image asset | bounded clean raster region with a real file and explicit slot | independently replaceable image node |
| editable HTML/UI node | reconstructed text, container, control, icon, simple geometry, or effect | separately editable code/canvas structure |

An image crop containing UI that will be rebuilt is not an independent image asset. A complete UI screenshot is not a cleaned visual base.

## Fidelity tiers are not element types

The tiers below are a fidelity-risk axis, not a universal taxonomy of UI elements. Every node must be described independently by:

1. `role`: what the element is semantically, such as visual subject, container, text, icon, control, data visual, navigation, or background;
2. `renderType`: how it will be rebuilt, such as `code`, `vector-asset`, `raster-asset`, or `mixed`;
3. `provenance`: where an asset came from, such as `source`, `imagegen`, `generated-svg`, `cleaned-reference`, `local-library`, or `code-authored`;
4. `fidelityTier`: how harmful a mismatch would be for the confirmed reference.

Any UI visual subject, distinctive geometry, branded visual, or data-rich visual can be an `anchor`. A generic icon, divider, or minor shadow can be `detail` or `decoration`. Determine the category by visual mismatch cost, not by product domain.

## Fixed fidelity tiers

Classify every node into one tier:

| Tier | Meaning | Default strategy |
|---|---|---|
| `anchor` | visual subject or geometry that establishes the screen identity | preserve from the reference; extract/clean or reproduce with measured code; do not replace with a generic asset |
| `structure` | regions whose position, size, count, and hierarchy define the UI | reproduce from measured bounds and explicit parent/child relationships |
| `detail` | icons, labels, progress marks, small decorations, local typography and shadows | use verified resources or code; match the recorded semantic and visual role |
| `decoration` | non-semantic glow, texture, grain, ambient light, minor effects | code or generate when needed, without changing anchors or structure |

Judge each region by how much replacing or simplifying it would change the confirmed UI image. A complex element may have an `anchor` parent with `structure` and `detail` children; do not force the entire element into one implementation route.

The strategy is domain-independent: lock the reference, identify high-cost visual anchors, preserve their source appearance, and translate the remaining structure through measured geometry and verified resources.

## Reference-fidelity visual base

Use the exact term `参考保真视觉底图` (`reference-fidelity visual base`) for the cleaned full-canvas scene derived from the locked reference and placed beneath rebuilt controls.

The source must be the complete locked UI image at its original dimensions. Do not first extract a local subject region, apply `object-fit: cover`, or resize the image to a local slot. Cleaning precedes slot placement; the cleaned result must preserve the full canvas boundary.

The required processing chain is:

```text
locked AI UI reference
→ remove text, buttons, icons, cards, and controls that will be reconstructed
→ repair background regions revealed by removal
→ retain the UI visual subject together with visually dependent projection, reflection, lighting, background atmosphere, texture, and spatial relationships
→ clean the complete original image, or generate a same-size repair only for the identified removed regions, at the exact canvas width, height, and aspect ratio
→ place it as the bottom-most image layer at 100% width × 100% height
→ reconstruct editable controls above it
```

This layer must not be the complete UI screenshot with controls left in place. It may fill the full canvas after cleanup, while all reconstructed UI remains separate and editable above it. The cleaned image is itself one replaceable `raster-asset` with `provenance: cleaned-reference`; do not claim that its internal visual content remains separately editable. `Edge-to-edge` requires exact-size, exact-ratio preparation and placement; it must not be achieved by stretching. Record `sourceBounds`, `destinationBounds` equal to the canvas bounds, `retainedLayers`, `removedUI`, `fitMode: "exact-fill"`, and `internalEditability: false`.

When the visual subject and its projection, reflection, illumination, atmospheric background, or texture depend on each other, keep them together in this base by default. Make this decision during decomposition: do not first create separate nominal assets and merge them later. Split them only when the user explicitly requests independent editability and real clean assets can be produced without visual drift. Do not create several nominally editable layers from contaminated crops or approximations. Isolated covers, textures, or illustrations with clear independent boundaries remain independent image assets.

## Asset action

For each image-bearing node, choose exactly one primary action:

- `reuse`: use the confirmed source asset as-is;
- `extract-clean`: remove UI contamination, remove background, or correct edges while preserving the source appearance; crop only for an intentionally bounded independent asset after full-reference cleaning, never before making a `参考保真视觉底图`;
- `code-render`: reproduce with shapes, gradients, lines, or verified vectors;
- `generate-region`: generate only the identified region when no usable source exists;
- `composite`: combine independent source, code, and asset children.

Prefer `reuse` or `extract-clean` for anchors. Use `generate-region` when a clean asset cannot be recovered reliably. Use `composite` when visually dependent parts would otherwise drift materially. For a cleaned composite, remove rebuilt UI and record `sourceBounds`, `destinationBounds`, `retainedLayers`, `removedUI`, and `fitMode`. Never use keyword placeholders, random stock imagery, or an unverified generic substitute for a confirmed anchor.

## Asset and container are one decision

Every raster or vector asset must be planned together with its destination container:

- source bounds and intended crop;
- destination bounds and aspect ratio;
- `contain`, `cover`, stretch, or transparent overlay behavior;
- alpha requirement and edge treatment;
- whether the asset should fill the container or intentionally float within it;
- background/texture continuity at the container edge.

Slot-bound visual assets should fill their destination container according to the recorded fit plan. Do not apply `object-cover` or an equivalent crop by default when it would remove meaningful content. If aspect ratios conflict, clean or regenerate the asset at the destination ratio; do not stretch or silently crop. A crop that removes meaningful content, exposes a rectangular matte, leaves a visible gap, or duplicates an overlaid UI element is a fidelity failure.

When a visual anchor becomes the visual base, clean away all rebuilt UI while retaining the UI visual subject and its dependent visual context. Keep the resulting asset at the full locked canvas boundary; this is a cleaned full-canvas raster beneath editable UI, not a flattened UI screenshot.

## One-pass fidelity gate

Before the primary canvas write, confirm:

- the locked reference path is the one being used;
- the locked source is complete, uncropped, and still at its original pixel dimensions;
- every anchor has a non-generic source action;
- every major container has measured bounds;
- every asset has a destination fit plan;
- if using `参考保真视觉底图`, its source bounds equal the full locked reference and its destination bounds equal the full canvas;
- every icon has a verified target representation;
- no node depends on a keyword placeholder.

This preflight is intended to prevent expensive repair cycles. It is not a request for a separate user approval round.
