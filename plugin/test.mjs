// Run the plugin's unit tests.
//
// The sources import each other by the ".js" specifier that NodeNext wants,
// which node's own type stripping does not map back to ".ts" -- so the tests
// are bundled with the esbuild that is already in the tree and handed to
// node's built-in runner. No test framework, no extra dependency.
import { build } from "esbuild";
import { spawnSync } from "node:child_process";
import { globSync } from "node:fs";
import { basename } from "node:path";

const entryPoints = globSync("src/**/*.test.ts");
if (entryPoints.length === 0) {
  console.error("no test files found");
  process.exit(1);
}

await build({
  entryPoints,
  bundle: true,
  platform: "node",
  format: "esm",
  outdir: "dist/test",
  sourcemap: "inline",
  external: ["node:*"],
});

const res = spawnSync(
  process.execPath,
  ["--test", "--enable-source-maps", ...entryPoints.map((f) => `dist/test/${basename(f, ".ts")}.js`)],
  { stdio: "inherit" },
);
process.exit(res.status ?? 1);
