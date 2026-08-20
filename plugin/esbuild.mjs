// Build the plugin bundle.
//
// This lives in a file rather than an npm script because the banner below
// contains parentheses and quotes that a shell mangles when the whole esbuild
// invocation is a one-line "scripts.build" string.
import { build } from "esbuild";

await build({
  entryPoints: ["src/plugin.ts"],
  bundle: true,
  platform: "node",
  format: "esm",
  outfile: "dist/plugin.js",
  sourcemap: true,
  // ws is CommonJS and does a dynamic require("events"). ESM has no require,
  // so esbuild's shim throws the moment the module loads and the plugin exits
  // 1 -- which Stream Deck reports only as "Process stopped (unexpected)".
  // Giving the bundle a real require satisfies it. The same class of bug was
  // fixed for rollup in ebdfa6f and returned when the build moved to esbuild.
  banner: {
    js: "import { createRequire as __cr } from 'module';\nconst require = __cr(import.meta.url);",
  },
});
