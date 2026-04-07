#!/usr/bin/env bash
set -euo pipefail

PLUGIN_UUID="com.phew.blue.homeops"
OUT_DIR="../dist-plugin"

cd "$(dirname "$0")"

echo "Building TypeScript..."
npm run build

echo "Assembling plugin package..."
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/bin"
mkdir -p "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/imgs"

cp dist/plugin.js         "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/bin/"
cp dist/plugin.js.map     "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/bin/" 2>/dev/null || true
cp -r imgs/               "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/imgs/"
cp manifest.json          "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/"

echo "Plugin built at $OUT_DIR/${PLUGIN_UUID}.sdPlugin"
