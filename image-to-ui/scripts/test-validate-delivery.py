#!/usr/bin/env python3
"""Small regression suite for the deterministic image-to-ui delivery gate."""

from __future__ import annotations

import base64
import copy
import importlib.util
import json
import struct
import tempfile
import zlib
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate-delivery.py"
SPEC = importlib.util.spec_from_file_location("image_to_ui_validator", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    rows = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def node(node_id: str, parent_id: str | None, children: list[str], order: int, role: str, bounds: dict, render_type: str, **extra: object) -> dict:
    result = {
        "id": node_id,
        "parentId": parent_id,
        "children": children,
        "order": order,
        "bounds": bounds,
        "role": role,
        "renderType": render_type,
        "provenance": "code-authored",
        "assetAction": "composite" if render_type == "mixed" else "code-render",
        "assetId": None,
        "targetKind": role,
        "targets": {"mastergo": {"kind": "frame", "route": "native", "expectedNodeType": "FRAME"}},
    }
    result.update(extra)
    return result


def build_fixture(root: Path) -> tuple[Path, Path, Path]:
    assets_dir = root / "assets"
    assets_dir.mkdir()
    source_bytes = png(16, 9, (18, 24, 32))
    base_bytes = png(16, 9, (32, 44, 60))
    (root / "reference.png").write_bytes(source_bytes)
    (assets_dir / "visual-base.png").write_bytes(base_bytes)
    lucide_source = SKILL_ROOT / "assets" / "icons" / "lucide" / "icons" / "settings.svg"
    lucide_copy = assets_dir / "settings.svg"
    lucide_copy.write_bytes(lucide_source.read_bytes())
    (root / "preview.png").write_bytes(png(160, 90, (36, 48, 64)))

    root_bounds = {"x": 0, "y": 0, "width": 1600, "height": 900}
    raster_fields = {
        "assetId": "visual-base",
        "assetPath": "assets/visual-base.png",
        "width": 16,
        "height": 9,
        "hasAlpha": False,
        "sourceCrop": "none-before-cleaning",
        "fitMode": "exact-fill",
        "provenance": "cleaned-reference",
        "assetAction": "extract-clean",
    }
    vector_fields = {
        "assetId": "lucide:settings",
        "assetPath": "assets/settings.svg",
        "provenance": "local-library",
        "assetAction": "resolve-icon",
    }
    nodes = [
        node("root", None, ["base", "label", "settings"], 0, "screen", root_bounds, "mixed", structuralOnly=True),
        node("base", "root", [], 0, "visual-base", root_bounds, "raster-asset", **raster_fields),
        node("label", "root", [], 1, "text", {"x": 100, "y": 100, "width": 400, "height": 80}, "code", text="Ready"),
        node("settings", "root", [], 2, "icon", {"x": 1450, "y": 60, "width": 48, "height": 48}, "vector-asset", **vector_fields),
    ]
    ir = {
        "referenceId": "fixture-v1",
        "decompositionVersion": "fixture-v1:confirmed",
        "revision": 1,
        "changes": [],
        "source": {
            "path": "reference.png",
            "requestedCanvas": {"width": 1600, "height": 900, "aspectRatio": "16:9"},
            "sourceDimensions": {"width": 16, "height": 9, "aspectRatio": "16:9"},
            "targetDimensions": {"width": 1600, "height": 900, "aspectRatio": "16:9"},
            "normalization": {"mode": "uniform-scale", "scaleX": 100, "scaleY": 100, "crop": False, "stretch": False},
        },
        "assets": [
            {"renderType": "raster-asset", **raster_fields},
            {"renderType": "vector-asset", **vector_fields},
        ],
        "nodes": nodes,
        "presentationRows": [
            {"id": "base-row", "component": "Screen", "label": "Visual base", "count": 1, "implementation": ["raster-asset"], "editableResult": ["image"], "nodeIds": ["base"]},
            {"id": "label-row", "component": "Screen", "label": "Label", "count": 1, "implementation": ["code"], "editableResult": ["text"], "nodeIds": ["label"]},
            {"id": "icon-row", "component": "Screen", "label": "Settings", "count": 1, "implementation": ["vector-asset"], "editableResult": ["icon"], "nodeIds": ["settings"]},
        ],
        "targets": {
            "html": {"path": "index.html", "layoutMode": "uniform-scale", "verification": "fast"},
            "mastergo": {"verification": "fast"},
        },
        "verification": {"visual": {"status": "inspected", "evidenceType": "local-file", "evidence": "preview.png"}},
    }
    ir_path = root / "ui-ir.json"
    ir_path.write_text(json.dumps(ir, indent=2), encoding="utf-8")

    icon_svg = lucide_copy.read_text(encoding="utf-8").replace(
        "<svg", '<svg data-asset-id="lucide:settings" data-icon-source="lucide:settings"', 1
    )
    data_url = "data:image/png;base64," + base64.b64encode(base_bytes).decode("ascii")
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}}html,body{{margin:0;min-height:100%}}body{{display:grid;place-items:center;min-height:100dvh}}svg{{display:block;width:100%;height:100%}}
.screen{{position:relative;width:min(100%,calc(100dvh * 16 / 9));aspect-ratio:16/9;container-type:inline-size;overflow:hidden}}
.base{{position:absolute;inset:0;width:100%;height:100%}}.label{{position:absolute;left:6.25cqw;top:11.11cqh;font-size:3cqw}}
.icon-box{{position:absolute;right:6.25cqw;top:6.66cqh;width:3cqw;height:3cqw}}
</style></head><body><main class="screen" data-node-id="root" data-ui-root data-design-width="1600" data-design-height="900">
<img class="base" data-node-id="base" data-asset-id="visual-base" src="{data_url}" alt="">
<div class="label" data-node-id="label">Ready</div><span class="icon-box" data-node-id="settings">{icon_svg}</span></main></body></html>'''
    html_path = root / "index.html"
    html_path.write_text(html, encoding="utf-8")
    return ir_path, html_path, root / "preview.png"


def expect_error(errors: list[str], fragment: str) -> None:
    if not any(fragment in error for error in errors):
        raise AssertionError(f"expected error containing {fragment!r}, got: {errors}")


def test_selector_relationships() -> None:
    icon_attrs = {"class": "icon-box"}
    play_ancestry = [("div", {"class": "play-main"}), ("main", {"class": "screen"})]
    favorite_ancestry = [("div", {"class": "favorite"}), ("main", {"class": "screen"})]
    assert VALIDATOR.selector_matches_node(".play-main .icon-box", icon_attrs, "span", play_ancestry)
    assert not VALIDATOR.selector_matches_node(".play-main .icon-box", icon_attrs, "span", favorite_ancestry)
    assert VALIDATOR.selector_matches_node(".play-main > .icon-box", icon_attrs, "span", play_ancestry)
    assert not VALIDATOR.selector_matches_node(".play-main > .icon-box", icon_attrs, "span", [("div", {"class": "inner"}), *play_ancestry])
    assert VALIDATOR.selector_matches_node(".play-main.icon-box", {"class": "play-main icon-box"}, "span", [])
    assert VALIDATOR.error_category("HTML root aspect-ratio must exactly match targetDimensions") == "html-contract"
    assert VALIDATOR.error_category("Lucide icon geometry does not match cached icon") == "asset"
    assert VALIDATOR.error_category("node card has invalid bounds") == "canonical-ir"
    assert VALIDATOR.error_category("verification.visual must record status 'inspected'") == "visual"


def main() -> int:
    test_selector_relationships()
    with tempfile.TemporaryDirectory(prefix="image-to-ui-validator-") as temp:
        root = Path(temp)
        ir_path, html_path, preview_path = build_fixture(root)
        valid = VALIDATOR.validate(ir_path, html_path, None, preview_path, True)
        if valid:
            raise AssertionError(f"valid HTML fixture failed: {valid}")
        valid_target = VALIDATOR.validate(ir_path, None, "mastergo", preview_path, True)
        if valid_target:
            raise AssertionError(f"valid MasterGo fixture failed: {valid_target}")

        original_html = html_path.read_text(encoding="utf-8")
        data_url = "data:image/png;base64," + base64.b64encode((root / "assets" / "visual-base.png").read_bytes()).decode("ascii")
        css_asset_html = original_html.replace(
            f'<img class="base" data-node-id="base" data-asset-id="visual-base" src="{data_url}" alt="">',
            '<div class="base" data-node-id="base" data-asset-id="visual-base"></div>',
        ).replace(".base{position:absolute", f'.base{{background-image:url("{data_url}");position:absolute')
        html_path.write_text(css_asset_html, encoding="utf-8")
        css_asset_errors = VALIDATOR.validate(ir_path, html_path)
        if css_asset_errors:
            raise AssertionError(f"valid CSS data-URL asset fixture failed: {css_asset_errors}")

        html_path.write_text(original_html.replace("width:min(100%,calc(100dvh * 16 / 9))", "width:100%;height:100%"), encoding="utf-8")
        expect_error(VALIDATOR.validate(ir_path, html_path), "must not combine width:100% and height:100%")

        html_path.write_text(original_html.replace("src=\"data:image/png;base64,", "src=\"assets/visual-base.png\" data-unused=\"data:image/png;base64,"), encoding="utf-8")
        expect_error(VALIDATOR.validate(ir_path, html_path), "external/local resource references")

        html_path.write_text(original_html.replace('d="M9.671 4.136', 'd="M0 0'), encoding="utf-8")
        expect_error(VALIDATOR.validate(ir_path, html_path), "geometry does not match cached icon")

        html_path.write_text(original_html.replace("svg{display:block;width:100%;height:100%}", "svg{display:block;width:100%}"), encoding="utf-8")
        expect_error(VALIDATOR.validate(ir_path, html_path), "inline svg for node settings must declare height:100%")

        html_path.write_text(original_html.replace("width:3cqw;height:3cqw", "width:3cqw"), encoding="utf-8")
        expect_error(VALIDATOR.validate(ir_path, html_path), "icon container for node settings must declare design-space width and height")

        html_path.write_text(original_html.replace("svg{display:block;width:100%;height:100%}", "svg{display:block}"), encoding="utf-8")
        expect_error(VALIDATOR.validate(ir_path, html_path), "inline svg for node settings must declare width:100%")

        html_path.write_text(original_html.replace("3cqw;height:3cqw", "3vw;height:3cqw"), encoding="utf-8")
        expect_error(VALIDATOR.validate(ir_path, html_path), "descendants must scale from the root")

        data = json.loads(ir_path.read_text(encoding="utf-8"))
        missing_visual = copy.deepcopy(data)
        missing_visual.pop("verification")
        ir_path.write_text(json.dumps(missing_visual), encoding="utf-8")
        expect_error(VALIDATOR.validate(ir_path, html_path, None, preview_path, True), "verification.visual")

        bad_ratio = copy.deepcopy(data)
        bad_ratio["source"]["sourceDimensions"] = {"width": 1672, "height": 941, "aspectRatio": "16:9"}
        ir_path.write_text(json.dumps(bad_ratio), encoding="utf-8")
        ratio_errors = VALIDATOR.validate(ir_path, None)
        expect_error(ratio_errors, "aspectRatio does not exactly match")
        expect_error(ratio_errors, "sourceDimensions and targetDimensions")

        bad_zoom = copy.deepcopy(data)
        bad_zoom["targets"]["html"]["previewZoom"] = {"enabled": True, "minPercent": 60, "maxPercent": 200, "stepPercent": 10}
        ir_path.write_text(json.dumps(bad_zoom), encoding="utf-8")
        expect_error(VALIDATOR.validate(ir_path, html_path), "previewZoom.minPercent must be 50")

        visual_text = copy.deepcopy(data)
        visual_text["nodes"].append({
            "id": "avatar-eye",
            "parentId": "root",
            "children": [],
            "order": 2,
            "bounds": {"x": 10, "y": 10, "width": 8, "height": 8},
            "role": "avatar-eye",
            "text": "•",
            "renderType": "code",
            "provenance": "code-authored",
            "assetAction": "code-render",
            "assetId": None,
            "targetKind": "shape",
        })
        visual_text["nodes"][0]["children"].append("avatar-eye")
        visual_text["presentationRows"].append({
            "id": "avatar-eye-row",
            "component": "Avatar",
            "label": "Avatar eye",
            "count": 1,
            "implementation": ["code"],
            "editableResult": ["shape"],
            "nodeIds": ["avatar-eye"],
        })
        ir_path.write_text(json.dumps(visual_text), encoding="utf-8")
        visual_text_errors = VALIDATOR.validate(ir_path, html_path)
        expect_error(visual_text_errors, "visual primitive node avatar-eye")

    print("PASS: validator positive and negative regression fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
