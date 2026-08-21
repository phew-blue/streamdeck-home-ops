// plugin/src/draw.ts
//
// The key artwork, rasterised.
//
// Each tile is drawn into an RGB buffer and encoded as a PNG. Drawing rather
// than shipping images means the gauge is continuous -- it shows 27% as 27%,
// not as the nearest pre-rendered step -- and the plugin carries no megabytes
// of generated base64.
//
// Anti-aliasing is by supersampling: every pixel is sampled SS x SS times and
// averaged. At 144px with SS=3 that is ~187k samples per tile, which is
// immaterial next to the kubectl calls these tiles used to make.
import { encodePng } from "./png.js";

const SIZE = 144;
const SS = 3;

/** Phew Blue tokens (brand/tokens/colors.json). */
export const BRAND = {
  aqua: "#1de9b6",
  gold: "#ffd166",
  coral: "#ff6e6e",
  sky: "#40c4ff",
  grey: "#8c929a",
  bg: "#16181b",
  track: "#393e46",
} as const;

type RGB = [number, number, number];

function rgbOf(hex: string): RGB {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

/**
 * Product brand colours, for the marks.
 *
 * A product's own colour identifies it faster than a status tint does, and
 * these tiles say their state in the title anyway. Flux and Kubernetes are the
 * published brand blues; Talos keeps the Phew Blue aqua, since its mark is
 * monochrome and its brand blue is too close to the background to read at
 * 144px.
 */
export const PRODUCT: Record<string, string> = {
  flux: "#5468ff",
  kubernetes: "#326ce5",
  talos: BRAND.aqua,
};

/** The accent for a 0-100 reading: comfortable, busy, or in trouble. */
export function band(pct: number): string {
  if (pct > 80) return BRAND.coral;
  if (pct > 50) return BRAND.gold;
  return BRAND.aqua;
}

/**
 * Render a tile.
 *
 * `sample` returns the colour at a point in tile space, or null for the
 * background. It is called per subsample, so it must be cheap and must not
 * allocate.
 */
function render(sample: (x: number, y: number) => RGB | null): string {
  const bg = rgbOf(BRAND.bg);
  const buf = new Uint8Array(SIZE * SIZE * 3);
  const inv = 1 / (SS * SS);
  for (let py = 0; py < SIZE; py++) {
    for (let px = 0; px < SIZE; px++) {
      let r = 0, g = 0, b = 0;
      for (let sy = 0; sy < SS; sy++) {
        for (let sx = 0; sx < SS; sx++) {
          const x = px + (sx + 0.5) / SS;
          const y = py + (sy + 0.5) / SS;
          const c = sample(x, y) ?? bg;
          r += c[0]; g += c[1]; b += c[2];
        }
      }
      const o = (py * SIZE + px) * 3;
      buf[o] = Math.round(r * inv);
      buf[o + 1] = Math.round(g * inv);
      buf[o + 2] = Math.round(b * inv);
    }
  }
  return encodePng(SIZE, SIZE, buf);
}

const BAR_HEIGHT = 12;

/**
 * A band of the status colour across the top.
 *
 * The default, for anything that is a count, a version or a duration: nothing
 * about it implies a scale the number does not have.
 */
export function barTile(accent: string): string {
  const a = rgbOf(accent);
  return render((_x, y) => (y < BAR_HEIGHT ? a : null));
}

const CX = SIZE / 2;
const CY = SIZE / 2;
// Sized so the two-line title sits inside the ring rather than across it.
// The inner clear span is 2*(RADIUS-THICK/2) = 88px, which comfortably holds a
// label and a value at the key's default 12pt.
const RADIUS = 58;
const THICK = 14;
const START = 135;      // degrees, clockwise from +x, y down
const SWEEP = 270;

/**
 * A dial, for readings that genuinely run 0-100.
 *
 * Only used where a maximum exists. Drawing an arc for a pod count would imply
 * a ceiling the number does not have.
 */
export function gaugeTile(accent: string, fraction: number): string {
  const f = Math.max(0, Math.min(1, fraction));
  const a = rgbOf(accent);
  const track = rgbOf(BRAND.track);
  const inner = RADIUS - THICK / 2;
  const outer = RADIUS + THICK / 2;
  const filled = SWEEP * f;
  return render((x, y) => {
    const dx = x - CX;
    const dy = y - CY;
    const r = Math.sqrt(dx * dx + dy * dy);
    if (r < inner || r > outer) return null;
    // Angle measured from START, increasing clockwise, wrapped to [0,360).
    let deg = (Math.atan2(dy, dx) * 180) / Math.PI - START;
    while (deg < 0) deg += 360;
    if (deg > SWEEP) return null;   // the open wedge at the bottom
    return deg <= filled ? a : track;
  });
}

/**
 * A product mark, filled in the status colour.
 *
 * `polys` are 24x24 polygons -- the Simple Icons outlines flattened at build
 * time -- scaled to the tile and filled by even-odd, so counters (the hole in
 * a letter, the gap in the Kubernetes helm) come out as holes.
 */
export function logoTile(polys: number[][][], accent: string, scale = 0.56): string {
  const a = rgbOf(accent);
  const span = SIZE * scale;
  const off = (SIZE - span) / 2;
  // Sit the mark high, leaving the lower third clear for the version, which is
  // drawn as a bottom-aligned title.
  const offY = 10;
  const k = span / 24;
  const pts = polys.map((p) => p.map(([x, y]) => [off + x! * k, offY + y! * k] as const));
  return render((x, y) => {
    let crossings = 0;
    for (const poly of pts) {
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const [xi, yi] = poly[i]!;
        const [xj, yj] = poly[j]!;
        if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) crossings++;
      }
    }
    return crossings % 2 === 1 ? a : null;
  });
}
