import commonjs from "@rollup/plugin-commonjs";
import { nodeResolve } from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";

export default {
  input: "src/plugin.ts",
  output: {
    file: "dist/plugin.js",
    format: "esm",
    sourcemap: true,
  },
  plugins: [
    typescript({ tsconfig: "./tsconfig.json" }),
    nodeResolve({ browser: false, exportConditions: ["node"] }),
    commonjs(),
  ],
  external: [
    // Node.js built-ins — Stream Deck provides these
    "child_process", "crypto", "events", "fs", "http", "https",
    "net", "os", "path", "stream", "tls", "url", "util", "zlib",
  ],
};
