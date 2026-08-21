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
 * The dial with nothing filled: the ring drawn as bare track.
 *
 * A tile's shape says what it measures, so a CPU reading is a dial whether or
 * not the deployment declares a limit -- swapping in a bar for the unlimited
 * ones made a page of CPU tiles read as two different metrics. There is still
 * no ceiling to fill against, so nothing is filled and no denominator is
 * invented; the title carries the absolute figure ("88m"), which is what
 * separates this from a bounded tile sitting at 0%.
 */
export function emptyGauge(): string {
  return memo("gauge:empty", () => gaugeTile(BRAND.grey, 0));
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

// --- The readings, worded and dressed -------------------------------------
//
// The two lines of a key's title are label then value, and the rules are the
// same for every tile: the label line always names the metric, and a caveat is
// appended to it rather than put in its place. These live here, next to the
// artwork they pick, so the wording and the shape cannot drift apart.

/** What a key should be showing: its two-line title, and its artwork. */
export interface Face {
  title: string;
  image: string;
}

/**
 * A CPU or memory reading for a deployment.
 *
 * `limit` is 0 when the deployment declares none, which is the common case.
 */
export function usageFace(metric: "cpu" | "ram", used: number, limit: number): Face {
  const label = metric.toUpperCase();
  if (limit > 0) {
    const pct = used / limit;
    return {
      title: `${label}\n${Math.round(pct * 100)}%`,
      image: gauge(band(pct * 100), pct),
    };
  }
  const unit = metric === "cpu" ? "m" : "Mi";
  return { title: `${label}\n${used}${unit}`, image: emptyGauge() };
}

/**
 * A readiness reading for a deployment.
 *
 * Restarts are a caveat on the number rather than the number itself, so they
 * ride on the label -- appended to it, not in place of it. An earlier version
 * replaced the word, which put "2r 1/1" beside "pods 1/1" and left the label
 * line no longer saying what it counted.
 */
export function podsFace(ready: number, desired: number, restarts: number): Face {
  const accent = ready === 0 ? BRAND.coral
    : ready < desired ? BRAND.gold
    : BRAND.aqua;
  const label = restarts > 0 ? `pods ${restarts}r` : "pods";
  return { title: `${label}\n${ready}/${desired}`, image: bar(accent) };
}
