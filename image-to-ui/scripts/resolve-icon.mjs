#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const libraryDir = path.resolve(scriptDir, "../assets/icons/lucide");
const upstreamDir = path.join(libraryDir, "icons");
const overrideDir = path.join(libraryDir, "overrides");
const aliases = JSON.parse(fs.readFileSync(path.join(libraryDir, "aliases.json"), "utf8"));
const tags = JSON.parse(fs.readFileSync(path.join(libraryDir, "tags.json"), "utf8"));
const packageInfo = JSON.parse(fs.readFileSync(path.join(libraryDir, "package.json"), "utf8"));

const args = process.argv.slice(2);
const queryParts = [];
let outputMode = "path";
let copyTo = null;

for (let index = 0; index < args.length; index += 1) {
  const value = args[index];
  if (value === "--json") outputMode = "json";
  else if (value === "--inline") outputMode = "inline";
  else if (value === "--copy-to") copyTo = args[++index];
  else queryParts.push(value);
}

const query = queryParts.join(" ").trim();
if (!query) {
  console.error("Usage: node scripts/resolve-icon.mjs <meaning> [--json|--inline] [--copy-to <directory>]");
  process.exit(1);
}

function normalize(value) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_\s]+/g, "-")
    .replace(/[^\p{L}\p{N}-]+/gu, "")
    .replace(/-+/g, "-");
}

function validIconName(value) {
  return /^[a-z0-9-]+$/.test(value);
}

function iconPath(iconName) {
  if (!validIconName(iconName)) return null;
  const override = path.join(overrideDir, `${iconName}.svg`);
  if (fs.existsSync(override)) return { path: override, source: "override" };
  const upstream = path.join(upstreamDir, `${iconName}.svg`);
  if (fs.existsSync(upstream)) return { path: upstream, source: "upstream" };
  return null;
}

const normalizedQuery = normalize(query);
const aliasName = aliases[query] ?? aliases[normalizedQuery];
const directNames = [aliasName, normalizedQuery, ...normalizedQuery.split("-")].filter(Boolean);

let match = null;
for (const iconName of directNames) {
  const located = iconPath(iconName);
  if (located) {
    match = { iconName, ...located, match: iconName === aliasName ? "alias" : "exact" };
    break;
  }
}

if (!match) {
  const queryTokens = new Set(normalizedQuery.split("-").filter(Boolean));
  let best = null;
  for (const [iconName, iconTags] of Object.entries(tags)) {
    const located = iconPath(iconName);
    if (!located) continue;
    const searchable = [iconName, ...iconTags].map(normalize);
    let score = 0;
    for (const token of queryTokens) {
      if (iconName === token) score += 10;
      if (iconName.split("-").includes(token)) score += 4;
      if (searchable.includes(token)) score += 3;
      if (searchable.some((item) => item.includes(token))) score += 1;
    }
    if (score > 0 && (!best || score > best.score || (score === best.score && iconName < best.iconName))) {
      best = { iconName, score, ...located, match: "semantic" };
    }
  }
  match = best;
}

if (!match) {
  const result = { status: "unresolved", query, library: "lucide", version: packageInfo.version };
  console.error(JSON.stringify(result, null, 2));
  process.exit(2);
}

let selectedPath = match.path;
if (copyTo) {
  const destinationDir = path.resolve(copyTo);
  fs.mkdirSync(destinationDir, { recursive: true });
  selectedPath = path.join(destinationDir, `${match.iconName}.svg`);
  fs.copyFileSync(match.path, selectedPath);
}

const result = {
  status: "resolved",
  query,
  library: "lucide",
  version: packageInfo.version,
  license: "ISC",
  iconName: match.iconName,
  match: match.match,
  source: match.source,
  sourcePath: match.path,
  outputPath: selectedPath
};

if (outputMode === "json") console.log(JSON.stringify(result, null, 2));
else if (outputMode === "inline") console.log(fs.readFileSync(match.path, "utf8"));
else console.log(selectedPath);
