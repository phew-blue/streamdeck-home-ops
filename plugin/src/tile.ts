// plugin/src/tile.ts
//
// Which artwork a reading gets, and a cache so it is drawn once.
//
// The split between image and title matters. The image is artwork only -- bar,
// dial or product mark -- and the label and value are the key's TITLE, which
// Stream Deck draws itself. An earlier version drew the value into the image
// and cleared the title; when Stream Deck declined the image the key went
// completely blank, with no error in any log. This way the reading cannot be
// lost, and the artwork is purely additive.
import { barTile, gaugeTile, logoTile, band, BRAND, PRODUCT } from "./draw.js";
import type { Poly } from "./logos.js";

export { band, BRAND, PRODUCT };

// Rendering a tile is ~187k subsamples and a deflate. That is nothing once, and
// wasteful four times a minute for a value that has not moved, so results are
// kept. The key space is small and bounded: five bar colours, a hundred and one
// gauge steps per colour, and a mark per product per colour.
const cache = new Map<string, string>();

function memo(key: string, make: () => string): string {
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const made = make();
  cache.set(key, made);
  return made;
}

/** A band of the status colour: counts, versions, durations. */
export function bar(accent: string): string {
  return memo(`bar:${accent}`, () => barTile(accent));
}

/**
 * A dial, rounded to whole percent.
 *
 * Rounding is what makes the cache finite; a gauge is 144px across, so a
 * fraction of a percent is well under a pixel of arc.
 */
export function gauge(accent: string, fraction: number): string {
  const pct = Math.max(0, Math.min(100, Math.round(fraction * 100)));
  return memo(`gauge:${accent}:${pct}`, () => gaugeTile(accent, pct / 100));
}

/**
 * A product mark, in that product's own colour.
 *
 * The metric id carries the product name (<product>_version), so the colour
 * comes from there rather than from kromgo's status tint: a Flux mark that is
 * not Flux blue reads as a generic badge.
 */
export function logo(product: string, polys: Poly[]): string {
  const accent = PRODUCT[product] ?? BRAND.sky;
  return memo(`logo:${product}:${accent}`, () => logoTile(polys, accent));
}

/**
 * Choose the artwork for a value.
 *
 * A trailing % is what makes a dial meaningful, and it is also the only thing
 * that reliably signals a 0-100 range in kromgo's output.
 */
export function forValue(value: string, accent: string): string {
  const m = /^(\d+(?:\.\d+)?)\s*%$/.exec(value.trim());
  return m ? gauge(accent, Number(m[1]) / 100) : bar(accent);
}

/** kromgo's colour names, and anything else, mapped onto the brand palette. */
export function accentFor(name: string | undefined): string {
  switch ((name ?? "").toLowerCase()) {
    case "green": return BRAND.aqua;
    case "orange":
    case "yellow": return BRAND.gold;
    case "red": return BRAND.coral;
    case "blue": return BRAND.sky;
    default: return BRAND.grey;
  }
}
