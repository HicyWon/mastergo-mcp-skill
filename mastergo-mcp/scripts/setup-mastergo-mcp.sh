#!/usr/bin/env bash
set -euo pipefail

# MasterGo Vibe MCP configuration helper for Codex Desktop and generic MCP clients.
# Source for the package/connection shape: https://mastergo.com/help/MG/MCP

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PACKAGE='@mastergo/vibe-mcp'
PORT=50678
ASSUME_YES=0
WRITE_TOML=1
WRITE_JSON=1
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"

usage() {
    cat <<'EOF'
Usage: setup-mastergo-mcp.sh [options]

Options:
  --yes           Apply changes without the interactive prompt. Use only after
                  the user has explicitly approved the configuration write.
  --port PORT     mgmcp port (default: 50678).
  --codex-only    Only update Codex Desktop config.toml.
  --json-only     Only update the generic .mcp.json file.
  --help          Show this help.

Environment:
  CODEX_HOME      Codex configuration directory (default: ~/.codex).
EOF
}

while (($#)); do
    case "$1" in
        --yes)
            ASSUME_YES=1
            shift
            ;;
        --port)
            if (($# < 2)); then
                echo -e "${RED}Missing value for --port.${NC}" >&2
                exit 2
            fi
            PORT="$2"
            shift 2
            ;;
        --codex-only)
            WRITE_TOML=1
            WRITE_JSON=0
            shift
            ;;
        --json-only)
            WRITE_TOML=0
            WRITE_JSON=1
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || ((PORT < 1 || PORT > 65535)); then
    echo -e "${RED}Invalid port: $PORT${NC}" >&2
    exit 2
fi

if ! command -v npx >/dev/null 2>&1; then
    echo -e "${RED}npx was not found. Install Node.js 18 or newer, then rerun this script.${NC}" >&2
    echo "Official download: https://nodejs.org/" >&2
    exit 1
fi

NPX_PATH="$(command -v npx)"
NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])' 2>/dev/null || true)"
if ! [[ "$NODE_MAJOR" =~ ^[0-9]+$ ]] || ((NODE_MAJOR < 18)); then
    echo -e "${RED}Node.js 18 or newer is required. Current version: $(node -v 2>/dev/null || echo unknown)${NC}" >&2
    exit 1
fi

TOML_PATH="$CODEX_HOME_DIR/config.toml"
JSON_PATH="$CODEX_HOME_DIR/.mcp.json"

echo -e "${CYAN}MasterGo Vibe MCP configuration${NC}"
echo "  npx: $NPX_PATH"
echo "  endpoint: http://localhost:$PORT"
((WRITE_TOML)) && echo "  update: $TOML_PATH ([mcp_servers.mastergo] only)"
((WRITE_JSON)) && echo "  update: $JSON_PATH (mcpServers.mastergo only)"
echo "  Existing unrelated configuration will be preserved. Changed files receive a timestamped backup."
echo "  On the next MCP launch, npx -y may download $PACKAGE if it is not already cached."

if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo -e "${GREEN}mgmcp is listening on port $PORT.${NC}"
else
    echo -e "${YELLOW}mgmcp is not currently listening on port $PORT. Configuration can still be written.${NC}"
    echo "Open MasterGo in its desktop client or connected Chrome session before using the MCP tools."
fi

if ((ASSUME_YES == 0)); then
    if [[ ! -t 0 ]]; then
        echo -e "${RED}Refusing a non-interactive configuration write without --yes.${NC}" >&2
        echo "Review the paths above and rerun with --yes only after explicit user approval." >&2
        exit 3
    fi
    read -r -p "Apply these configuration changes? [y/N] " REPLY
    case "$REPLY" in
        y|Y|yes|YES) ;;
        *)
            echo "No changes made."
            exit 0
            ;;
    esac
fi

python3 - "$NPX_PATH" "$PORT" "$TOML_PATH" "$JSON_PATH" "$WRITE_TOML" "$WRITE_JSON" <<'PYEOF'
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

npx_path, port, toml_arg, json_arg, write_toml_arg, write_json_arg = sys.argv[1:]
port = int(port)
toml_path = Path(toml_arg).expanduser()
json_path = Path(json_arg).expanduser()
write_toml = write_toml_arg == "1"
write_json = write_json_arg == "1"
timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")

toml_block = (
    "[mcp_servers.mastergo]\n"
    f'command = {json.dumps(npx_path)}\n'
    f'args = ["-y", "@mastergo/vibe-mcp", "--url=http://localhost:{port}"]\n'
    "startup_timeout_sec = 120\n"
)
json_server = {
    "command": npx_path,
    "args": ["-y", "@mastergo/vibe-mcp", f"--url=http://localhost:{port}"],
}


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    old_mode = path.stat().st_mode if path.exists() else None
    if path.exists():
        backup = path.with_name(f"{path.name}.bak.{timestamp}")
        shutil.copy2(path, backup)
        print(f"  backup: {backup}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        if old_mode is not None:
            os.chmod(temp_name, old_mode)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def plan_toml(path: Path) -> tuple[str, str]:
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    section = re.compile(
        r"(?ms)^\[mcp_servers\.mastergo\][ \t]*\n.*?(?=^\[|\Z)"
    )
    if section.search(original):
        updated = section.sub(toml_block + "\n", original, count=1)
    else:
        separator = "" if not original else ("\n" if original.endswith("\n") else "\n\n")
        updated = original + separator + toml_block
    return original, updated


def plan_json(path: Path) -> tuple[str, str]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON in {path}: {exc}. No JSON changes were made.")
        if not isinstance(data, dict):
            raise SystemExit(f"Expected a JSON object in {path}. No JSON changes were made.")
    else:
        data = {}
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise SystemExit(f"Expected mcpServers to be an object in {path}. No JSON changes were made.")
    original = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    servers["mastergo"] = json_server
    updated = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return original, updated


plans: list[tuple[Path, str, str]] = []
if write_toml:
    original, updated = plan_toml(toml_path)
    plans.append((toml_path, original, updated))
if write_json:
    original, updated = plan_json(json_path)
    plans.append((json_path, original, updated))

# Validate and construct every requested change before writing either file.
for path, original, updated in plans:
    if updated == original:
        print(f"  unchanged: {path}")
        continue
    atomic_write(path, updated)
    print(f"  updated: {path}")
PYEOF

echo -e "${GREEN}Configuration complete.${NC}"
echo "Fully quit and restart Codex Desktop, then verify with tool_search(\"mastergo\") or mcp__mastergo__get_version."
echo "A resources/list 'Method not found' response is not a failure for MasterGo Vibe MCP."
