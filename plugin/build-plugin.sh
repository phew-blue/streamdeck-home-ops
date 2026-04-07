#!/usr/bin/env bash
set -euo pipefail

PLUGIN_UUID="com.phew.blue.homeops"
OUT_DIR="../dist-plugin"

cd "$(dirname "$0")"

echo "Building TypeScript..."
npm run build

echo "Assembling plugin package..."
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/${PLUGIN_UUID}.sdPlugin"

cp -r dist/          "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/"
cp -r imgs/          "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/"
cp manifest.json     "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/"
cp package.json      "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/"
cp -r node_modules/  "$OUT_DIR/${PLUGIN_UUID}.sdPlugin/"

echo "Plugin built at $OUT_DIR/${PLUGIN_UUID}.sdPlugin"
