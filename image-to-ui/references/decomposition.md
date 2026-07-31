# UI Decomposition

The decomposition is the only mandatory user confirmation before canvas generation. When the source begins as a sketch or brief, generate the final UI image first. Decompose that locked image, not the sketch, and present the image and decomposition as one confirmation package.

## Contents

- Analyze in this order
- Fixed user-facing format
- Presentation rules
- Internal UI IR tree
- Rendering routes
- Composite-widget granularity gate
- Lineage gate
- Minimum manifest shape
- Confirmation rules

## Analyze in this order

1. Establish the viewport, complete original pixel dimensions, orientation, aspect ratio, and screen boundary. Do not crop the source during analysis.
2. Mark major components and stacking order.
3. Inventory every visible text, control, icon, image, texture, and meaningful decoration.
4. Mark repeated elements and exact counts.
5. Split each component into code, vector asset, raster asset (from source, cleaning, or image generation), or mixed implementation parts.
6. Record visual properties and asset boundaries that must survive reconstruction.
7. Mark uncertainty and decisions that require user input.

## Fixed user-facing format

Present Screen information first:

```text
参考图: <path or image ID>
拆解版本: <reference hash/version>
源尺寸: <width × height>
目标画布: <width × height>
方向 / 比例: <orientation> / <aspect ratio>
归一化: <none or uniform-scale + factor>
```

Then create one section per named component, in visual/tree order. Use the component name as a heading and always use this exact five-column table:

| 元素 | 数量 | 实现方式 | 可编辑结果 | 关键说明 |
|---|---:|---|---|---|
| 卡片容器 | 1 | `code` | 圆角 Frame | 玻璃态样式 |
| 纹理图像 | 1 | 独立位图资产（AI生成） | 独立图片层 | `renderType: raster-asset`，保持为位图，不矢量化 |
| 主要操作按钮 | 1 | `code + vector-asset` | Button + 独立 Icon | 内部拆为按钮容器与语义图标 |

For example:

```markdown
### Composite Panel

| 元素 | 数量 | 实现方式 | 可编辑结果 | 关键说明 |
|---|---:|---|---|---|
| 卡片容器 | 1 | `code` | 圆角 Frame | 玻璃态样式 |
| 纹理图像 | 1 | 独立位图资产（AI生成） | 独立图片层 | `renderType: raster-asset`，保持为位图，不矢量化 |
| 标题文本 | 1 | `code` | Text | 文案来自用户 brief |
| 次要操作图标 | 1 | `vector-asset` | 独立 Icon | 记录明确语义 |
| 主要操作按钮 | 1 | `code + vector-asset` | Button + 独立 Icon | 容器和图标分别编辑 |
| 补充操作图标 | 1 | `vector-asset` | 独立 Icon | 记录明确语义 |
```

## Presentation rules

- Do not show `ID`, level columns, `parentId`, `children`, `children-below`, raw `assetAction`, target resource IDs, or adapter-only nesting by default.
- Do not add parent summary rows that merely repeat the component heading. The heading already establishes the component boundary.
- Keep rows in visible reading order: container/background first, then the reference-fidelity visual base where applicable, followed by text, controls, icons, and independently replaceable image regions.
- List every independently editable or separately replaceable part. Do not summarize an entire composite component as “mixed, editable.” Do not list the internal ingredients of a deliberately unsplit visual base as separate rows.
- Enumerate every Dock, toolbar, or navigation icon separately by meaning. A generic “icons × 5” row is insufficient.
- A row may represent one atomic node or a small composite control when that is more readable. For example, a primary action may use `code + vector-asset`, but `关键说明` must state that its container and icon remain separately editable.
- `实现方式` may contain one route or an explicit combination of routes only when the row intentionally represents a small composite control. The internal UI IR must still give each independently editable child exactly one route; an intentionally unsplit visual base remains one `raster-asset` route.
- `可编辑结果` names concrete editable results such as `Text`, `Image`, `Rounded Frame`, `Button + Icon`, or `Vector Path`; do not write only “可编辑.”
- Put only user-relevant fidelity constraints, semantic assumptions, source-of-text notes, or unresolved limitations in `关键说明`.
- Keep geometry, stable IDs, parentage, exact asset actions, platform mappings, and verification status in the internal manifest.

## Internal UI IR tree

The user-facing tables are a review projection, not the structural schema. Build the platform-neutral UI IR as an unlimited-depth tree. Do not impose level 1/2/3 fields or a maximum depth.

Every UI IR node must include:

| Group | Fields |
|---|---|
| Identity | `id`, `parentId`, `children`, `order`, `role`, `name` |
| Quantity | `repeatGroup`, `count`, `state` |
| Geometry | `bounds`, `zIndex`, `layoutRelation`, `overlap` |
| Content | `text`, `iconMeaning`, `dataValue` |
| Visual | `fill`, `border`, `radius`, `cutCorners`, `decorativeLines`, `shadow`, `opacity`, `typography` |
| Source | `renderType`, `provenance`, `fidelityTier`, `assetAction`, `assetId`, `assetPath`, `width`, `height`, `hasAlpha`, `sourceCrop`, `fitMode` |
| Target | platform-neutral `targetKind`, `editableChildren`, `fallback`; platform routes live under `targets.<adapter>` |
| Confidence | `confidence`, `notes` |

Derive tree depth only from `parentId` and `children`. Every node has exactly one `renderType`, one `assetAction`, one `assetId` or `null`, and one platform-neutral `targetKind`. Put HTML, MasterGo, and Figma representations under `targets.<adapter>`. Every `raster-asset` and `vector-asset` node requires a non-null `assetId`.

## Materialized UI IR and asset contract

The UI IR must be saved as a real file, normally `ui-ir.json` beside the HTML or canvas handoff. It must not exist only in internal context. Use `renderType` for representation and `provenance` for origin. For every image asset node, populate all of the following before delivery:

```json
{
  "assetId": "visual-subject-v1",
  "assetPath": "assets/visual-subject-v1.png",
  "renderType": "raster-asset",
  "provenance": "imagegen",
  "width": 1200,
  "height": 760,
  "hasAlpha": true,
  "sourceCrop": "none-before-cleaning",
  "fitMode": "contain"
}
```

The file at `assetPath` must exist, and the final HTML or canvas manifest must reference the same `assetId` and path. If an asset is unavailable, stop and report the blocker. Do not replace it with a crop of the complete UI screenshot, a CSS approximation, or an unreported placeholder. A standalone generated SVG uses `renderType: vector-asset` and `provenance: generated-svg`; an inlined local-library or generated SVG remains a `vector-asset` carrying its source `assetId`; only SVG geometry authored directly as delivery code uses `renderType: code` and `assetAction: code-render`.

For backward compatibility, accept legacy `renderType: generated-asset` only as an input alias. Normalize it to `renderType: raster-asset`, resolve `provenance`, verify the file format, and record the migration in `changes`; do not emit the legacy label in new tables or manifests.

Give every user-facing row an internal stable `presentationRowId`. Copy each confirmed five-column row into `presentationRows` before generating nodes or assets; preserve its component, label, count, implementation route, and editable result. Do not replace independently editable child rows in a component with one component-summary row. A deliberately unsplit visual base is not a component summary: it is the confirmed single asset boundary, and multiple semantic rows may reference its one node only when they describe the same retained visual base. Store a many-to-many-safe mapping:

```json
{
  "presentationRows": [
    {
      "id": "panel-primary-action-row",
      "component": "Composite Panel",
      "label": "Composite control",
      "count": 1,
      "implementation": ["code", "vector-asset"],
      "editableResult": ["button", "icon"],
      "nodeIds": ["panel-primary-action", "panel-primary-action-icon"]
    }
  ]
}
```

The table is a user-editable specification after it is presented. When the user changes a row through conversation, preserve its `presentationRowId` when the semantic element remains the same; update the mapped UI IR node fields, asset record, and target mapping in the same revision. If the user adds, removes, or splits a row, add, remove, or split the corresponding IR nodes and mappings. Record the synchronized revision in `ui-ir.json`:

```json
{
  "revision": 3,
  "changes": [
    {
      "presentationRowId": "panel-texture-row",
      "before": {"implementation": "generated-asset"},
      "after": {"implementation": "独立位图资产（AI生成）"},
      "affectedNodeIds": ["panel-texture"],
      "affectedAssetIds": ["album-art-v2"]
    }
  ]
}
```

Do not continue from a stale manifest after a conversational table edit. Re-run the lineage and asset checks before generating HTML or writing to a canvas.

One row may map to multiple nodes only for a small composite control or an explicit repeat group; it must not map an entire component's unrelated visible children. Multiple semantic rows describing one deliberately unsplit visual base may reference the same single raster node. Multiple tightly related rows may reference a shared structural parent. Every required UI IR node must be covered by at least one presentation row or be marked `structuralOnly: true` with a documented reason. Structural-only nodes may provide layout wrappers, masks, or clipping groups; they must not hide visible content from the user-facing tables.

## Rendering routes

| Route | Use for | Typical output |
|---|---|---|
| `code` | layout, containers, cards, buttons, dividers, independently editable simple effects, text | editable frame, text, shape, or CSS style |
| `vector-asset` | icons, logos, simple illustrations, existing vector marks | local SVG or verified library/component instance |
| `raster-asset` | bitmap regions from source, cleaning, or image generation | independent local bitmap; use `provenance` to record origin |
| `mixed` | internal parent composed of several routes | parent group with explicit child nodes |

`mixed` is an internal composition label, not a sufficient implementation decision. Image-bearing children remain image assets; editable text, controls, and icons remain separate nodes.

## Composite-widget granularity gate

For each composite widget, inventory at minimum:

- frame or container;
- every visible text node;
- every non-semantic visual primitive that must be independently edited, such as avatar eyes/mouths, dots, arrows, or decorative marks; represent it as a shape/vector/path node or verified vector asset, never as text glyphs;
- every independently replaceable image or visual region; if a visual subject and its dependent effects are intentionally unsplit, inventory them as one `参考保真视觉底图` item;
- every icon or logo;
- every control and repeated control;
- every independently editable meaningful line, mask, glow, or effect that affects fidelity. Do not turn non-editable internal light, shadow, or texture ingredients of the visual base into separate rows.

Example internal structure:

```text
Composite Panel
├── card frame · code
├── texture asset · raster-asset (`provenance: imagegen`)
├── text group
│   ├── primary label · code
│   └── secondary label · code
└── action group
    ├── secondary action icon · vector-asset
    ├── primary action button
    │   ├── button container · code
    │   └── semantic icon · vector-asset
    └── supplementary action icon · vector-asset
```

Do not flatten this tree because the user-facing table is shorter. Do not turn raster visual regions, textures, covers, or generated illustrations into vector/code because their parent is mixed. Do not flatten text, controls, or icons into an image child.

## Lineage gate

Before generation, verify:

1. every presentation row maps to one or more existing UI IR node IDs;
2. every visible UI IR node is covered by a presentation row;
3. every `structuralOnly` node has a valid non-visible structural reason;
4. `parentId`, `children`, `order`, bounds, repeat counts, and semantic roles are internally consistent;
5. every IR node has exactly one `renderType`, `assetAction`, `assetId` or `null`, and platform-neutral `targetKind`; every raster/vector asset node has a non-null `assetId`;
6. every raster node maps to an image fill or verified image route and has explicit provenance;
7. every vector node maps to a verified vector route or explicit fallback;
8. missing, ambiguous, or silently omitted mappings block canvas generation.

For a `参考保真视觉底图`, keep the cleaned scene as one `raster-asset` node with `provenance: cleaned-reference`, `fitMode: "exact-fill"`, full-canvas `destinationBounds`, bottom-most `zIndex`, and `internalEditability: false`. Record `sourceBounds` equal to the complete locked image and `sourceCrop: "none-before-cleaning"`. All removed controls must appear as separate editable nodes above it.

## Minimum manifest shape

```json
{
  "referenceId": "sha256-or-stable-image-id",
  "decompositionVersion": "referenceId:v1",
  "source": {
    "path": "ui-reference.png",
    "brief": "...",
    "requestedCanvas": {"width": 1440, "height": 900, "aspectRatio": "8:5"},
    "sourceDimensions": {"width": 1440, "height": 900, "aspectRatio": "8:5"},
    "targetDimensions": {"width": 1440, "height": 900, "aspectRatio": "8:5"},
    "normalization": {"mode": "none", "scaleX": 1, "scaleY": 1, "crop": false, "stretch": false}
  },
  "presentationRows": [
    {
      "id": "panel-primary-action-row",
      "component": "Composite Panel",
      "label": "主要操作按钮",
      "count": 1,
      "implementation": ["code", "vector-asset"],
      "editableResult": ["button", "icon"],
      "nodeIds": ["panel-primary-action", "panel-primary-action-icon"]
    }
  ],
  "nodes": [
    {
      "id": "panel-primary-action",
      "parentId": "panel-actions",
      "children": ["panel-primary-action-icon"],
      "order": 2,
      "role": "button",
      "bounds": {"x": 400, "y": 690, "width": 56, "height": 56},
      "renderType": "code",
      "assetAction": "code-render",
      "assetId": null,
      "targetKind": "button",
      "targets": {"html": {"kind": "element", "route": "inline-code"}},
      "structuralOnly": false
    },
    {
      "id": "panel-primary-action-icon",
      "parentId": "panel-primary-action",
      "children": [],
      "order": 0,
      "role": "icon",
      "bounds": {"x": 416, "y": 706, "width": 24, "height": 24},
      "renderType": "vector-asset",
      "assetAction": "resolve-icon",
      "assetId": "lucide:play",
      "targetKind": "icon",
      "targets": {"html": {"kind": "svg", "route": "inline-local-vector"}},
      "structuralOnly": false
    }
  ],
  "decisions": [],
  "status": "awaiting-user-confirmation"
}
```

## Confirmation rules

Always return, in this order: the locked image, Screen metadata, complete component-grouped five-column tables, then a short decision/limitation list. Internal JSON never replaces the user-facing tables.

Every image-generation or material image-edit pass invalidates the old decomposition. In the same response as the new image, regenerate all component tables from the new locked image. Never return only the new image or a brief regional summary.

Ask for visual-reference confirmation before decomposition. After that confirmation, present the complete tables and save a synchronized draft `ui-ir.json` whose `presentationRows` exactly copy those tables; mark the draft `awaiting-user-confirmation` and do not use it for HTML or canvas generation. Ask for decomposition feedback. For every requested change, update the table first and then the mapped UI IR nodes, assets, and target mappings in the same revision before asking again. Only after the user confirms the decomposition may the canonical UI IR be finalized and the output target selected or used. Keep the full presentation-row → UI IR → target mapping internal by default. For canvas output, tell the user whether mapping is ready, list unresolved fallbacks, and report verification differences. Show the complete mapping only when the user requests it.
