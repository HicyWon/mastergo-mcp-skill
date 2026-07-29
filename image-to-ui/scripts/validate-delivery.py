#!/usr/bin/env python3
"""Validate an image-to-ui canonical UI IR and optional self-contained HTML.

This checker intentionally validates only deterministic contracts: tree integrity,
presentation-row lineage, asset metadata/files, and HTML embedding/mapping. It
does not claim to judge visual similarity or whether an edited bitmap looks clean.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


REQUIRED_NODE_FIELDS = {
    "id",
    "parentId",
    "children",
    "order",
    "bounds",
    "role",
    "renderType",
    "provenance",
    "assetAction",
    "assetId",
    "targetKind",
}
REQUIRED_IMAGE_FIELDS = {
    "assetId",
    "assetPath",
    "renderType",
    "provenance",
    "width",
    "height",
    "hasAlpha",
    "sourceCrop",
    "fitMode",
    "assetAction",
}
REQUIRED_VECTOR_FIELDS = {"assetId", "assetPath", "renderType", "provenance", "assetAction"}
REQUIRED_ROW_FIELDS = {
    "id",
    "component",
    "label",
    "count",
    "implementation",
    "editableResult",
    "nodeIds",
}
RENDER_TYPES = {"code", "vector-asset", "raster-asset", "mixed"}
VISUAL_PRIMITIVE_ROLE_RE = re.compile(
    r"(?:^|[-_ ])(?:icon|avatar[-_ ]?(?:eye|mouth|face|expression)|eye|mouth|dot|marker|shape|line|path|glyph|decoration)(?:$|[-_ ])",
    re.IGNORECASE,
)
PLATFORM_PREFIXES = ("html-", "mastergo-", "figma-")
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
SVG_GEOMETRY_TAGS = {"path", "circle", "ellipse", "line", "polyline", "polygon", "rect"}
SVG_GEOMETRY_ATTRIBUTES = {
    "d", "cx", "cy", "r", "rx", "ry", "x", "x1", "x2", "y", "y1", "y2",
    "width", "height", "points", "transform",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_text(value: str) -> str:
    return " ".join(value.split())


def listify(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def parse_ratio(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"\s*(\d+)\s*[:/]\s*(\d+)\s*", value)
    if not match:
        return None
    left, right = int(match.group(1)), int(match.group(2))
    if left <= 0 or right <= 0:
        return None
    divisor = math.gcd(left, right)
    return left // divisor, right // divisor


def numeric_dimensions(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, dict):
        return None
    width, height = value.get("width"), value.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        return None
    return width, height


def parse_declarations(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    parts: list[str] = []
    start = 0
    quote: str | None = None
    depth = 0
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif char == ";" and depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    for part in parts:
        if ":" not in part:
            continue
        key, raw = part.split(":", 1)
        result[key.strip().lower()] = raw.strip()
    return result


def css_rule_blocks(styles: str) -> list[tuple[str, dict[str, str]]]:
    blocks: list[tuple[str, dict[str, str]]] = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", styles, re.S):
        selector = match.group(1).strip()
        if selector.startswith("@"):
            continue
        blocks.append((selector, parse_declarations(match.group(2))))
    return blocks


def selector_matches_node(selector: str, attrs: dict[str, str], tag: str | None = None) -> bool:
    """Recognize exact simple selectors without substring-matching sibling classes."""
    html_id = attrs.get("id")
    classes = set(attrs.get("class", "").split())
    for simple in selector.split(","):
        simple = simple.strip()
        compounds = [part for part in re.split(r"\s+|(?=[>+~])|(?<=[>+~])", simple) if part and part not in {">", "+", "~"}]
        terminal = compounds[-1] if compounds else simple
        terminal = re.sub(r":{1,2}[\w-]+(?:\([^)]*\))?", "", terminal)
        if "[data-ui-root]" in terminal:
            return "data-ui-root" in attrs
        if tag and re.search(rf"(?:^|[\s>+~]){re.escape(tag)}(?=$|[.#[:])", terminal):
            return True
        if html_id and re.search(rf"(?<![\w-])#{re.escape(html_id)}(?![\w-])", terminal):
            return True
        for class_name in classes:
            if re.search(rf"(?<![\w-])\.{re.escape(class_name)}(?![\w-])", terminal):
                return True
    return False


def declarations_for_element(
    css_rules: list[tuple[str, dict[str, str]]], attrs: dict[str, str], tag: str
) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for selector, rule in css_rules:
        if selector_matches_node(selector, attrs, tag):
            declarations.update(rule)
    declarations.update(parse_declarations(attrs.get("style", "")))
    return declarations


def design_space_size(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    normalized = re.sub(r"\s+", "", value.lower())
    if not normalized or re.search(r"(?:px|rem|em|vw|vh|vmin|vmax)\b", normalized):
        return False
    return bool(re.search(r"(?:cqw|cqh|%|cqmin|cqmax)\b", normalized))


def geometry_signature(tag: str, attrs: dict[str, str]) -> tuple[str, tuple[tuple[str, str], ...]]:
    values = tuple(sorted((key, re.sub(r"\s+", " ", value.strip())) for key, value in attrs.items() if key in SVG_GEOMETRY_ATTRIBUTES))
    return tag, values


def image_info(data: bytes) -> tuple[int, int, bool] | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 33:
        width, height, _depth, color_type = struct.unpack(">IIBB", data[16:26])
        has_alpha = color_type in {4, 6} or b"tRNS" in data
        return width, height, has_alpha

    if data.startswith(b"\xff\xd8"):
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in {0xD8, 0xD9}:
                continue
            if index + 2 > len(data):
                break
            length = struct.unpack(">H", data[index:index + 2])[0]
            if marker in set(range(0xC0, 0xC4)) | set(range(0xC5, 0xC8)) | set(range(0xC9, 0xCC)) | set(range(0xCD, 0xD0)):
                height, width = struct.unpack(">HH", data[index + 3:index + 7])
                return width, height, False
            index += max(length, 2)

    if data.startswith((b"GIF87a", b"GIF89a")) and len(data) >= 10:
        width, height = struct.unpack("<HH", data[6:10])
        return width, height, b"\x21\xf9\x04" in data

    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X" and len(data) >= 30:
            flags = data[20]
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            return width, height, bool(flags & 0x10)
    return None


class DeliveryHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.ignore_depth = 0
        self.node_stack: list[str | None] = []
        self.node_occurrences: dict[str, int] = {}
        self.node_text: dict[str, list[str]] = {}
        self.asset_embeddings: dict[str, list[bytes]] = {}
        self.asset_mappings: dict[str, list[tuple[str | None, str]]] = {}
        self.unmapped_text: list[str] = []
        self.external_refs: list[str] = []
        self.styles: list[str] = []
        self.node_attributes: dict[str, dict[str, str]] = {}
        self.node_tags: dict[str, str] = {}
        self.svg_geometry: dict[str, list[tuple[str, tuple[tuple[str, str], ...]]]] = {}
        self.svg_occurrences: list[dict[str, Any]] = []
        self.element_stack: list[tuple[str, dict[str, str]]] = []
        self._style_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}
        if tag == "body":
            self.in_body = True
        if tag in {"script", "noscript"}:
            self.ignore_depth += 1
        if tag == "style":
            self._style_depth += 1

        parent_node = self.node_stack[-1] if self.node_stack else None
        parent_element = self.element_stack[-1] if self.element_stack else None
        node_id = attrs_dict.get("data-node-id") or parent_node
        self.node_stack.append(node_id)
        self.element_stack.append((tag, attrs_dict))
        if "data-node-id" in attrs_dict:
            explicit = attrs_dict["data-node-id"]
            self.node_occurrences[explicit] = self.node_occurrences.get(explicit, 0) + 1
            self.node_attributes[explicit] = attrs_dict
            self.node_tags[explicit] = tag
        if node_id and tag in SVG_GEOMETRY_TAGS:
            self.svg_geometry.setdefault(node_id, []).append(geometry_signature(tag, attrs_dict))
        if tag == "svg":
            parent_tag, parent_attrs = parent_element if parent_element else (None, {})
            self.svg_occurrences.append({
                "ownerNodeId": node_id,
                "attrs": attrs_dict,
                "parentTag": parent_tag,
                "parentAttrs": parent_attrs,
            })

        for key in ("src", "href"):
            value = attrs_dict.get(key, "").strip()
            if value and not value.startswith(("data:", "#")):
                if not (tag == "a" and key == "href"):
                    self.external_refs.append(value)

        asset_id = attrs_dict.get("data-asset-id")
        if asset_id:
            self.asset_mappings.setdefault(asset_id, []).append((node_id, tag))
            candidates = [attrs_dict.get("src", ""), attrs_dict.get("style", "")]
            found = False
            for candidate in candidates:
                for match in re.finditer(r"data:([^;,]+)?(?:;charset=[^;,]+)?;base64,([A-Za-z0-9+/=\s]+)", candidate):
                    try:
                        payload = base64.b64decode(re.sub(r"\s+", "", match.group(2)), validate=True)
                    except ValueError:
                        continue
                    self.asset_embeddings.setdefault(asset_id, []).append(payload)
                    found = True
            if not found:
                self.asset_embeddings.setdefault(asset_id, [])
        if tag in VOID_TAGS:
            if self.node_stack:
                self.node_stack.pop()
            if self.element_stack:
                self.element_stack.pop()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "style" and self._style_depth:
            self._style_depth -= 1
        if tag in {"script", "noscript"} and self.ignore_depth:
            self.ignore_depth -= 1
        if self.node_stack:
            self.node_stack.pop()
        if self.element_stack:
            self.element_stack.pop()
        if tag == "body":
            self.in_body = False

    def handle_data(self, data: str) -> None:
        if self._style_depth:
            self.styles.append(data)
            return
        if not self.in_body or self.ignore_depth:
            return
        value = normalized_text(data)
        if not value:
            return
        node_id = self.node_stack[-1] if self.node_stack else None
        if node_id:
            self.node_text.setdefault(node_id, []).append(value)
        else:
            self.unmapped_text.append(value)


def svg_geometry_from_file(path: Path) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
    parser = DeliveryHTMLParser()
    try:
        parser.feed(f'<body><svg data-node-id="icon">{path.read_text(encoding="utf-8")}</svg></body>')
    except (OSError, UnicodeDecodeError):
        return []
    return parser.svg_geometry.get("icon", [])


def validate(
    ir_path: Path,
    html_path: Path | None,
    target: str | None = None,
    visual_evidence: Path | None = None,
    require_visual: bool = False,
) -> list[str]:
    errors: list[str] = []
    try:
        ir = json.loads(ir_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read UI IR: {exc}"]

    nodes = ir.get("nodes")
    rows = ir.get("presentationRows")
    assets = ir.get("assets")
    if not isinstance(nodes, list):
        return ["nodes must be an array"]
    if not isinstance(rows, list):
        errors.append("presentationRows must be an array")
        rows = []
    if not isinstance(assets, list):
        errors.append("assets must be an array")
        assets = []
    if not isinstance(ir.get("revision"), int) or ir.get("revision", 0) < 1:
        errors.append("revision must be a positive integer")
    if not isinstance(ir.get("changes", []), list):
        errors.append("changes must be an array")

    node_by_id: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{index}] must be an object")
            continue
        missing = REQUIRED_NODE_FIELDS - node.keys()
        if missing:
            errors.append(f"node {node.get('id', index)!r} missing fields: {', '.join(sorted(missing))}")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            errors.append(f"nodes[{index}] has invalid id")
            continue
        if node_id in node_by_id:
            errors.append(f"duplicate node id: {node_id}")
        node_by_id[node_id] = node
        render_type = node.get("renderType")
        if render_type not in RENDER_TYPES:
            errors.append(f"node {node_id} has invalid renderType: {render_type!r}")
        if render_type in {"raster-asset", "vector-asset"} and not node.get("assetId"):
            errors.append(f"asset node {node_id} must have a non-null assetId")
        target_kind = node.get("targetKind")
        if isinstance(target_kind, str) and (target_kind.startswith(PLATFORM_PREFIXES) or target_kind == "inline-svg"):
            errors.append(f"node {node_id} targetKind must be platform-neutral, got {target_kind!r}")
        role = str(node.get("role", ""))
        if isinstance(node.get("text"), str) and VISUAL_PRIMITIVE_ROLE_RE.search(role) and target_kind != "text":
            errors.append(
                f"visual primitive node {node_id} with role {role!r} must not use text; use a shape/vector/path node or verified vector asset"
            )
        bounds = node.get("bounds")
        if not isinstance(bounds, dict) or not all(isinstance(bounds.get(key), (int, float)) for key in ("x", "y", "width", "height")):
            errors.append(f"node {node_id} must have numeric x/y/width/height bounds")
        elif bounds["width"] < 0 or bounds["height"] < 0:
            errors.append(f"node {node_id} has negative bounds")

    roots = [node_id for node_id, node in node_by_id.items() if node.get("parentId") is None]
    if len(roots) != 1:
        errors.append(f"UI IR must have exactly one root node, found {len(roots)}")

    for node_id, node in node_by_id.items():
        children = node.get("children")
        if not isinstance(children, list):
            errors.append(f"node {node_id} children must be an array")
            continue
        for child_id in children:
            child = node_by_id.get(child_id)
            if child is None:
                errors.append(f"node {node_id} references missing child {child_id}")
            elif child.get("parentId") != node_id:
                errors.append(f"child {child_id} parentId does not point back to {node_id}")
        parent_id = node.get("parentId")
        if parent_id is not None:
            parent = node_by_id.get(parent_id)
            if parent is None:
                errors.append(f"node {node_id} references missing parent {parent_id}")
            elif node_id not in parent.get("children", []):
                errors.append(f"parent {parent_id} does not list child {node_id}")
            if parent is not None and isinstance(node.get("bounds"), dict) and isinstance(parent.get("bounds"), dict):
                child_bounds = node["bounds"]
                parent_bounds = parent["bounds"]
                if all(isinstance(child_bounds.get(key), (int, float)) for key in ("x", "y", "width", "height")) and all(isinstance(parent_bounds.get(key), (int, float)) for key in ("x", "y", "width", "height")):
                    outside = (
                        child_bounds["x"] < parent_bounds["x"]
                        or child_bounds["y"] < parent_bounds["y"]
                        or child_bounds["x"] + child_bounds["width"] > parent_bounds["x"] + parent_bounds["width"]
                        or child_bounds["y"] + child_bounds["height"] > parent_bounds["y"] + parent_bounds["height"]
                    )
                    intentional = node.get("allowOverflow") is True or node.get("overlap") == "intentional"
                    if outside and not intentional:
                        errors.append(f"node {node_id} bounds exceed parent {parent_id} without explicit intentional overlap")

    for node_id, node in node_by_id.items():
        child_orders = [node_by_id[child_id].get("order") for child_id in node.get("children", []) if child_id in node_by_id]
        if len(child_orders) != len(set(child_orders)):
            errors.append(f"node {node_id} has duplicate child order values")

    asset_by_id: dict[str, dict[str, Any]] = {}
    asset_bytes: dict[str, bytes] = {}
    source_path_value = ir.get("source", {}).get("path") if isinstance(ir.get("source"), dict) else None
    source_path = (ir_path.parent / source_path_value).resolve() if isinstance(source_path_value, str) else None
    source_hash = None
    if source_path is None or not source_path.is_file():
        errors.append("source.path must resolve to the complete locked reference file")
    else:
        source_data = source_path.read_bytes()
        source_hash = sha256(source_data)
        source_info = image_info(source_data)
        declared_source_dimensions = ir.get("source", {}).get("sourceDimensions")
        if source_info and isinstance(declared_source_dimensions, dict):
            if declared_source_dimensions.get("width") != source_info[0] or declared_source_dimensions.get("height") != source_info[1]:
                errors.append("sourceDimensions do not match the locked reference file")

    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            errors.append(f"assets[{index}] must be an object")
            continue
        render_type = asset.get("renderType")
        required_asset_fields = REQUIRED_IMAGE_FIELDS if render_type == "raster-asset" else REQUIRED_VECTOR_FIELDS
        missing = required_asset_fields - asset.keys()
        if missing:
            errors.append(f"asset {asset.get('assetId', index)!r} missing fields: {', '.join(sorted(missing))}")
        asset_id = asset.get("assetId")
        if not isinstance(asset_id, str) or not asset_id:
            errors.append(f"assets[{index}] has invalid assetId")
            continue
        if asset_id in asset_by_id:
            errors.append(f"duplicate assetId: {asset_id}")
        asset_by_id[asset_id] = asset
        asset_path_value = asset.get("assetPath")
        if not isinstance(asset_path_value, str) or not asset_path_value:
            continue
        asset_path = (ir_path.parent / asset_path_value).resolve()
        if not asset_path.is_file():
            errors.append(f"asset {asset_id} file does not exist: {asset_path_value}")
            continue
        data = asset_path.read_bytes()
        asset_bytes[asset_id] = data
        if render_type == "raster-asset":
            info = image_info(data)
            if info is None:
                errors.append(f"asset {asset_id} uses an unsupported or invalid raster format")
            else:
                width, height, has_alpha = info
                if asset.get("width") != width or asset.get("height") != height:
                    errors.append(f"asset {asset_id} metadata dimensions do not match file: declared {asset.get('width')}x{asset.get('height')}, actual {width}x{height}")
                if asset.get("hasAlpha") is not has_alpha:
                    errors.append(f"asset {asset_id} hasAlpha does not match file: declared {asset.get('hasAlpha')}, actual {has_alpha}")
        elif render_type == "vector-asset" and b"<svg" not in data[:2048].lower():
            errors.append(f"vector asset {asset_id} is not an SVG file")
        elif render_type not in {"raster-asset", "vector-asset"}:
            errors.append(f"asset {asset_id} has invalid renderType {render_type!r}")
        if source_hash and sha256(data) == source_hash:
            errors.append(f"asset {asset_id} is byte-identical to the complete reference image")

    for node_id, node in node_by_id.items():
        if node.get("renderType") not in {"raster-asset", "vector-asset"}:
            continue
        asset_id = node.get("assetId")
        asset = asset_by_id.get(asset_id)
        if asset is None:
            errors.append(f"asset node {node_id} references missing asset record {asset_id!r}")
            continue
        required_fields = REQUIRED_IMAGE_FIELDS if node.get("renderType") == "raster-asset" else REQUIRED_VECTOR_FIELDS
        for field in required_fields:
            if field in node and node.get(field) != asset.get(field):
                errors.append(f"asset node {node_id} field {field} disagrees with asset {asset_id}")
        for field in required_fields:
            if field not in node:
                errors.append(f"asset node {node_id} missing asset field {field}")

        if isinstance(asset_id, str) and asset_id.startswith("lucide:"):
            if node.get("assetAction") != "resolve-icon":
                errors.append(f"Lucide icon node {node_id} must use assetAction 'resolve-icon'")
            if node.get("provenance") != "local-library":
                errors.append(f"Lucide icon node {node_id} must use provenance 'local-library'")

    covered_nodes: set[str] = set()
    row_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"presentationRows[{index}] must be an object")
            continue
        missing = REQUIRED_ROW_FIELDS - row.keys()
        if missing:
            errors.append(f"presentation row {row.get('id', index)!r} missing fields: {', '.join(sorted(missing))}")
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id:
            continue
        if row_id in row_ids:
            errors.append(f"duplicate presentation row id: {row_id}")
        row_ids.add(row_id)
        node_ids = row.get("nodeIds")
        if not isinstance(node_ids, list) or not node_ids:
            errors.append(f"presentation row {row_id} must map to at least one node")
            continue
        visible_leaf_ids = []
        for node_id in node_ids:
            node = node_by_id.get(node_id)
            if node is None:
                errors.append(f"presentation row {row_id} references missing node {node_id}")
                continue
            covered_nodes.add(node_id)
            if not node.get("structuralOnly") and node.get("renderType") != "mixed":
                visible_leaf_ids.append(node_id)
        if len(visible_leaf_ids) > 3 and not row.get("repeatGroup"):
            errors.append(f"presentation row {row_id} maps {len(visible_leaf_ids)} visible leaf nodes; split component summaries into child-level rows")
        declared_routes = set(listify(row.get("implementation")))
        actual_routes = {node_by_id[node_id].get("renderType") for node_id in visible_leaf_ids}
        if not actual_routes.issubset(declared_routes):
            errors.append(f"presentation row {row_id} implementation {sorted(declared_routes)} does not cover mapped routes {sorted(actual_routes)}")

    for node_id, node in node_by_id.items():
        if node.get("structuralOnly"):
            continue
        if node_id not in covered_nodes:
            errors.append(f"visible node {node_id} is not covered by any presentation row")

    if target:
        top_targets = ir.get("targets")
        if not isinstance(top_targets, dict) or target not in top_targets:
            errors.append(f"top-level targets is missing {target!r}")
        for node_id, node in node_by_id.items():
            node_targets = node.get("targets")
            mapping = node_targets.get(target) if isinstance(node_targets, dict) else None
            if not isinstance(mapping, dict):
                errors.append(f"node {node_id} is missing targets.{target} mapping")
                continue
            if not isinstance(mapping.get("kind"), str) or not mapping.get("kind"):
                errors.append(f"node {node_id} targets.{target}.kind is required")
            if not isinstance(mapping.get("route"), str) or not mapping.get("route"):
                errors.append(f"node {node_id} targets.{target}.route is required")
            if node.get("renderType") == "vector-asset" and not (
                mapping.get("expectedNodeType") or mapping.get("fallback")
            ):
                errors.append(f"vector node {node_id} targets.{target} requires expectedNodeType or explicit fallback")

    source = ir.get("source", {})
    if isinstance(source, dict):
        requested_dimensions = numeric_dimensions(source.get("requestedCanvas"))
        declared_source_dimensions = numeric_dimensions(source.get("sourceDimensions"))
        target_dimensions_pair = numeric_dimensions(source.get("targetDimensions"))
        if requested_dimensions is None:
            errors.append("source.requestedCanvas must contain positive integer width and height")
        if declared_source_dimensions is None:
            errors.append("source.sourceDimensions must contain positive integer width and height")
        if target_dimensions_pair is None:
            errors.append("source.targetDimensions must contain positive integer width and height")

        for field in ("requestedCanvas", "sourceDimensions", "targetDimensions"):
            block = source.get(field)
            dimensions = numeric_dimensions(block)
            if dimensions and isinstance(block, dict):
                if "aspectRatio" not in block:
                    errors.append(f"source.{field}.aspectRatio is required")
                else:
                    declared_ratio = parse_ratio(block.get("aspectRatio"))
                    if declared_ratio is None or dimensions[0] * declared_ratio[1] != dimensions[1] * declared_ratio[0]:
                        errors.append(f"source.{field}.aspectRatio does not exactly match its dimensions")

        if requested_dimensions and target_dimensions_pair:
            if requested_dimensions[0] * target_dimensions_pair[1] != requested_dimensions[1] * target_dimensions_pair[0]:
                errors.append("requestedCanvas and targetDimensions must have exactly the same aspect ratio")
        if declared_source_dimensions and target_dimensions_pair:
            if declared_source_dimensions[0] * target_dimensions_pair[1] != declared_source_dimensions[1] * target_dimensions_pair[0]:
                errors.append("sourceDimensions and targetDimensions must have exactly the same aspect ratio before delivery")

        normalization = source.get("normalization", {})
        if isinstance(normalization, dict) and normalization.get("mode") == "uniform-scale":
            sx, sy = normalization.get("scaleX"), normalization.get("scaleY")
            if not isinstance(sx, (int, float)) or not isinstance(sy, (int, float)) or abs(sx - sy) > 1e-6:
                errors.append("uniform-scale normalization requires equal numeric scaleX and scaleY")
            if declared_source_dimensions and target_dimensions_pair and isinstance(sx, (int, float)) and isinstance(sy, (int, float)):
                expected_x = target_dimensions_pair[0] / declared_source_dimensions[0]
                expected_y = target_dimensions_pair[1] / declared_source_dimensions[1]
                if abs(sx - expected_x) > 1e-6 or abs(sy - expected_y) > 1e-6:
                    errors.append("normalization scaleX/scaleY must equal the ratios derived from real source and target dimensions")
        if isinstance(normalization, dict):
            for forbidden in ("crop", "stretch", "pad", "padding"):
                value = normalization.get(forbidden)
                if value not in (None, False, 0, "none"):
                    errors.append(f"normalization.{forbidden} must be false/none at delivery")
        target_dimensions = source.get("targetDimensions")
        if roots and isinstance(target_dimensions, dict):
            root_bounds = node_by_id[roots[0]].get("bounds", {})
            if root_bounds.get("width") != target_dimensions.get("width") or root_bounds.get("height") != target_dimensions.get("height"):
                errors.append("root bounds must match source.targetDimensions")

    if html_path is not None:
        try:
            html = html_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"cannot read HTML: {exc}")
            return errors
        parser = DeliveryHTMLParser()
        parser.feed(html)
        styles = "\n".join(parser.styles)
        for selector, declarations in css_rule_blocks(styles):
            matched_nodes = [node_id for node_id, attrs in parser.node_attributes.items() if selector_matches_node(selector, attrs)]
            for matched_node in matched_nodes:
                asset_id = parser.node_attributes.get(matched_node, {}).get("data-asset-id")
                if not asset_id:
                    continue
                for value in declarations.values():
                    for match in re.finditer(r"data:([^;,]+)?(?:;charset=[^;,]+)?;base64,([A-Za-z0-9+/=\s]+)", value):
                        try:
                            payload = base64.b64decode(re.sub(r"\s+", "", match.group(2)), validate=True)
                        except ValueError:
                            continue
                        parser.asset_embeddings.setdefault(asset_id, []).append(payload)

        if re.search(r"<link\b[^>]*rel=[\"']?stylesheet", html, re.I):
            errors.append("HTML is not self-contained: external stylesheet link found")
        if parser.external_refs:
            errors.append(f"HTML contains external/local resource references: {', '.join(sorted(set(parser.external_refs)))}")
        if parser.unmapped_text:
            errors.append(f"visible HTML text lacks data-node-id mapping: {parser.unmapped_text[:5]}")
        duplicates = sorted(node_id for node_id, count in parser.node_occurrences.items() if count != 1)
        if duplicates:
            errors.append(f"HTML data-node-id values must occur exactly once: {duplicates}")
        unknown_html_nodes = sorted(set(parser.node_occurrences) - set(node_by_id))
        if unknown_html_nodes:
            errors.append(f"HTML references unknown UI IR nodes: {unknown_html_nodes}")
        missing_html_nodes = sorted(
            node_id for node_id, node in node_by_id.items()
            if not node.get("structuralOnly") and node_id not in parser.node_occurrences
        )
        if missing_html_nodes:
            errors.append(f"HTML is missing visible UI IR nodes: {missing_html_nodes}")
        if roots and roots[0] not in parser.node_occurrences:
            errors.append(f"HTML is missing the root data-node-id {roots[0]!r}")

        for node_id, node in node_by_id.items():
            expected = node.get("text")
            if not isinstance(expected, str):
                continue
            actual = normalized_text(" ".join(parser.node_text.get(node_id, [])))
            if actual != normalized_text(expected):
                errors.append(f"HTML text mismatch for node {node_id}: expected {expected!r}, got {actual!r}")

        for asset_id, data in asset_bytes.items():
            if asset_by_id.get(asset_id, {}).get("renderType") != "raster-asset":
                continue
            embedded = parser.asset_embeddings.get(asset_id, [])
            if not embedded:
                errors.append(f"HTML does not embed canonical asset {asset_id} on an element with data-asset-id")
            elif not any(candidate == data for candidate in embedded):
                errors.append(f"HTML embedded bytes do not match canonical asset {asset_id}")
        unknown_assets = sorted(set(parser.asset_embeddings) - set(asset_by_id))
        if unknown_assets:
            errors.append(f"HTML embeds unknown assets: {unknown_assets}")

        for node_id, node in node_by_id.items():
            render_type = node.get("renderType")
            if render_type not in {"raster-asset", "vector-asset"}:
                continue
            asset_id = node.get("assetId")
            if not isinstance(asset_id, str) or not asset_id:
                continue
            mappings = parser.asset_mappings.get(asset_id, [])
            if not any(mapped_node == node_id for mapped_node, _tag in mappings):
                errors.append(f"HTML node {node_id} is not marked with its data-asset-id {asset_id!r}")
            if render_type == "vector-asset" and not any(mapped_node == node_id and tag == "svg" for mapped_node, tag in mappings):
                errors.append(f"HTML vector node {node_id} must be an inline svg carrying data-asset-id {asset_id!r}")

        lucide_root = Path(__file__).resolve().parent.parent / "assets" / "icons" / "lucide"
        for node_id, node in node_by_id.items():
            if node.get("role") != "icon":
                continue
            asset_id = node.get("assetId")
            if isinstance(asset_id, str) and asset_id.startswith("lucide:"):
                icon_name = asset_id.split(":", 1)[1]
                cached_candidates = [lucide_root / directory / f"{icon_name}.svg" for directory in ("overrides", "icons")]
                cached_path = next((candidate for candidate in cached_candidates if candidate.is_file()), None)
                if cached_path is None:
                    errors.append(f"Lucide icon node {node_id} references missing cached icon {icon_name!r}")
                attrs = next(
                    (occurrence["attrs"] for occurrence in parser.svg_occurrences if occurrence["ownerNodeId"] == node_id),
                    {},
                )
                if attrs.get("data-icon-source") != asset_id:
                    errors.append(f"HTML Lucide icon node {node_id} must declare data-icon-source={asset_id!r}")
                actual_geometry = parser.svg_geometry.get(node_id, [])
                expected_geometry = svg_geometry_from_file(cached_path) if cached_path else []
                if expected_geometry and actual_geometry != expected_geometry:
                    errors.append(f"HTML Lucide icon node {node_id} geometry does not match cached icon {icon_name!r}")
            else:
                resolution = node.get("iconResolution")
                if not isinstance(resolution, dict) or resolution.get("lucideAttempted") is not True or resolution.get("status") not in {"unresolved", "not-applicable"} or not resolution.get("reason"):
                    errors.append(f"non-Lucide icon node {node_id} must record a failed/not-applicable Lucide resolution attempt and reason")

        html_target = ir.get("targets", {}).get("html", {}) if isinstance(ir.get("targets"), dict) else {}
        layout_mode = html_target.get("layoutMode") if isinstance(html_target, dict) else None
        for css_url in re.findall(r"url\(\s*['\"]?([^)'\"\s]+)", styles, re.I):
            if not css_url.startswith(("data:", "#")):
                errors.append(f"HTML CSS contains external/local resource reference: {css_url}")
        if layout_mode not in {"uniform-scale", "reflow", "fixed"}:
            errors.append("targets.html.layoutMode must be 'uniform-scale', 'reflow', or 'fixed'")
        elif layout_mode == "uniform-scale":
            root_id = roots[0] if roots else None
            root_attrs = parser.node_attributes.get(root_id, {}) if root_id else {}
            if "data-ui-root" not in root_attrs:
                errors.append("uniform-scale HTML root must declare data-ui-root")
            target_dimensions_pair = numeric_dimensions(source.get("targetDimensions")) if isinstance(source, dict) else None
            if target_dimensions_pair:
                if root_attrs.get("data-design-width") != str(target_dimensions_pair[0]) or root_attrs.get("data-design-height") != str(target_dimensions_pair[1]):
                    errors.append("HTML root data-design-width/data-design-height must match targetDimensions")

            root_declarations: dict[str, str] = {}
            css_rules = css_rule_blocks(styles)
            for selector, declarations in css_rule_blocks(styles):
                if selector_matches_node(selector, root_attrs, parser.node_tags.get(root_id, "")):
                    root_declarations.update(declarations)
            root_declarations.update(parse_declarations(root_attrs.get("style", "")))
            css_ratio = parse_ratio(root_declarations.get("aspect-ratio"))
            if css_ratio is None:
                errors.append("uniform-scale HTML root must declare a literal fixed aspect-ratio")
            elif target_dimensions_pair and target_dimensions_pair[0] * css_ratio[1] != target_dimensions_pair[1] * css_ratio[0]:
                errors.append("HTML root aspect-ratio must exactly match targetDimensions")
            if root_declarations.get("width", "").lower() == "100%" and root_declarations.get("height", "").lower() == "100%":
                errors.append("HTML root must not combine width:100% and height:100% with aspect-ratio")
            if root_declarations.get("container-type", "").lower() not in {"inline-size", "size"}:
                errors.append("uniform-scale HTML root must establish its own CSS container query context")
            if re.search(r"@media\b", styles, re.I):
                errors.append("uniform-scale HTML must not use media-query reflow")
            if re.search(r"\bclamp\s*\(", styles, re.I):
                errors.append("uniform-scale HTML must not use clamp() minima that can desynchronize child scaling")
            fixed_minima = re.findall(r"min-(?:width|height)\s*:\s*(?!0(?:\D|$))[^;}]*(?:px|rem|em)", styles, re.I)
            if fixed_minima:
                errors.append("uniform-scale HTML contains non-zero fixed min-width/min-height constraints")
            viewport_pattern = re.compile(r"(?:\d|\.)\s*(?:vw|vh|dvw|dvh|svw|svh|lvw|lvh|vmin|vmax)\b", re.I)
            root_viewport_properties: set[str] = set()
            for selector, declarations in css_rules:
                matched_nodes = [node_id for node_id, attrs in parser.node_attributes.items() if selector_matches_node(selector, attrs)]
                for prop, value in declarations.items():
                    if not viewport_pattern.search(value):
                        continue
                    for matched_node in matched_nodes:
                        if matched_node != root_id:
                            errors.append(f"uniform-scale UI node {matched_node} uses viewport units in {prop}; descendants must scale from the root")
                        else:
                            root_viewport_properties.add(prop)
                            if prop not in {"width", "max-width"}:
                                errors.append(f"uniform-scale HTML root may use viewport units only for width/max-width, not {prop}")
            for prop, value in parse_declarations(root_attrs.get("style", "")).items():
                if viewport_pattern.search(value):
                    root_viewport_properties.add(prop)
                    if prop not in {"width", "max-width"}:
                        errors.append(f"uniform-scale HTML root may use viewport units only for width/max-width, not {prop}")
            if {"width", "height"}.issubset(root_viewport_properties) or {"max-width", "height"}.issubset(root_viewport_properties):
                errors.append("uniform-scale HTML root must not size both axes independently with viewport units")
            for occurrence in parser.svg_occurrences:
                owner_node_id = occurrence["ownerNodeId"]
                if not isinstance(owner_node_id, str) or owner_node_id not in node_by_id:
                    errors.append("uniform-scale inline svg must belong to a mapped UI IR node")
                    continue
                svg_declarations = declarations_for_element(css_rules, occurrence["attrs"], "svg")
                if svg_declarations.get("display", "").strip().lower() != "block":
                    errors.append(f"uniform-scale inline svg for node {owner_node_id} must declare display:block")
                if svg_declarations.get("width", "").strip().lower() != "100%":
                    errors.append(f"uniform-scale inline svg for node {owner_node_id} must declare width:100%")
                if svg_declarations.get("height", "").strip().lower() != "100%":
                    errors.append(f"uniform-scale inline svg for node {owner_node_id} must declare height:100%")
                parent_tag = occurrence["parentTag"]
                parent_attrs = occurrence["parentAttrs"]
                if not isinstance(parent_tag, str) or parent_tag == "svg":
                    errors.append(f"uniform-scale inline svg for node {owner_node_id} must have an explicit icon container")
                    continue
                parent_declarations = declarations_for_element(css_rules, parent_attrs, parent_tag)
                if not design_space_size(parent_declarations.get("width")) or not design_space_size(parent_declarations.get("height")):
                    errors.append(f"uniform-scale icon container for node {owner_node_id} must declare design-space width and height")
            if re.search(r"content\s*:\s*[\"'][^\"']+", styles, re.I):
                errors.append("visible CSS generated content is not mapped to a UI IR node")

        preview_zoom = html_target.get("previewZoom") if isinstance(html_target, dict) else None
        if preview_zoom is not None:
            if not isinstance(preview_zoom, dict) or preview_zoom.get("enabled") is not True:
                errors.append("targets.html.previewZoom must be an enabled object when present")
            else:
                expected_zoom = {"minPercent": 50, "maxPercent": 200, "stepPercent": 10}
                for key, expected in expected_zoom.items():
                    if preview_zoom.get(key) != expected:
                        errors.append(f"targets.html.previewZoom.{key} must be {expected}")

    verification = ir.get("verification")
    visual_record = verification.get("visual") if isinstance(verification, dict) else None
    if visual_evidence is not None:
        if not visual_evidence.is_file():
            errors.append(f"visual evidence file does not exist: {visual_evidence}")
        else:
            evidence_info = image_info(visual_evidence.read_bytes())
            if evidence_info is None:
                errors.append("visual evidence must be a readable PNG, JPEG, GIF, or supported WebP image")
    if require_visual:
        if not isinstance(visual_record, dict) or visual_record.get("status") != "inspected" or not visual_record.get("evidence"):
            errors.append("verification.visual must record status 'inspected' and a non-empty evidence reference")
        if visual_evidence is None and isinstance(visual_record, dict) and visual_record.get("evidenceType") == "local-file":
            errors.append("local-file visual evidence requires --visual-evidence")
        if visual_evidence is not None and isinstance(visual_record, dict):
            recorded = visual_record.get("evidence")
            if visual_record.get("evidenceType") != "local-file":
                errors.append("--visual-evidence requires verification.visual.evidenceType 'local-file'")
            elif isinstance(recorded, str):
                recorded_path = Path(recorded)
                if not recorded_path.is_absolute():
                    recorded_path = (ir_path.parent / recorded_path).resolve()
                if recorded_path != visual_evidence.resolve():
                    errors.append("verification.visual.evidence must reference the same file passed with --visual-evidence")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", required=True, type=Path, help="Path to canonical ui-ir.json")
    parser.add_argument("--html", type=Path, help="Path to self-contained HTML preview")
    parser.add_argument("--target", help="Canvas adapter name to preflight, for example mastergo or figma")
    parser.add_argument("--visual-evidence", type=Path, help="Optional local screenshot used for final visual verification")
    parser.add_argument("--require-visual", action="store_true", help="Require recorded visual inspection before completion")
    args = parser.parse_args()

    errors = validate(
        args.ir.resolve(),
        args.html.resolve() if args.html else None,
        args.target,
        args.visual_evidence.resolve() if args.visual_evidence else None,
        args.require_visual,
    )
    if errors:
        print(f"FAIL: {len(errors)} validation error(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: canonical UI IR and delivery contract are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
