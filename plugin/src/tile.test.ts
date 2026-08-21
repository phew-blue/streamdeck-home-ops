// plugin/src/tile.test.ts
//
// The tile vocabulary, checked by shape rather than by pixels.
//
// What matters here is that a metric always gets the same kind of artwork and
// the label line always names the metric; the artwork itself is a PNG and is
// only compared for identity (same reading -> same cached image).
//
// Run with: npm test  (node's own runner, no test framework in the tree)
import test from "node:test";
import assert from "node:assert/strict";

import { bar, gauge, emptyGauge, podsFace, usageFace, BRAND, band } from "./tile.js";

const lines = (title: string) => title.split("\n");

test("CPU keeps the dial whether or not a limit exists", () => {
  const bounded = usageFace("cpu", 250, 1000);
  const unbounded = usageFace("cpu", 88, 0);

  assert.equal(bounded.image, gauge(band(25), 0.25));
  assert.equal(unbounded.image, emptyGauge());
  // The point of the change: neither one is a bar.
  assert.notEqual(bounded.image, bar(BRAND.sky));
  assert.notEqual(unbounded.image, bar(BRAND.sky));
});

test("a bounded reading is a percentage, an unbounded one keeps its unit", () => {
  assert.deepEqual(lines(usageFace("cpu", 250, 1000).title), ["CPU", "25%"]);
  assert.deepEqual(lines(usageFace("cpu", 88, 0).title), ["CPU", "88m"]);
  assert.deepEqual(lines(usageFace("ram", 512, 1024).title), ["RAM", "50%"]);
  assert.deepEqual(lines(usageFace("ram", 412, 0).title), ["RAM", "412Mi"]);
});

test("an empty dial is not the same tile as a dial reading zero", () => {
  // Both rings are unfilled, so the titles are what separate them.
  assert.equal(lines(usageFace("cpu", 0, 1000).title)[1], "0%");
  assert.equal(lines(usageFace("cpu", 0, 0).title)[1], "0m");
});

test("the dial's accent follows the band", () => {
  assert.equal(usageFace("cpu", 100, 1000).image, gauge(BRAND.aqua, 0.1));
  assert.equal(usageFace("cpu", 700, 1000).image, gauge(BRAND.gold, 0.7));
  assert.equal(usageFace("cpu", 900, 1000).image, gauge(BRAND.coral, 0.9));
});

test("restarts append to the label instead of replacing it", () => {
  assert.deepEqual(lines(podsFace(1, 1, 0).title), ["pods", "1/1"]);
  assert.deepEqual(lines(podsFace(1, 1, 2).title), ["pods 2r", "1/1"]);
  // Every pods tile still starts its label with the metric.
  for (const restarts of [0, 1, 17]) {
    assert.ok(lines(podsFace(1, 1, restarts).title)[0]!.startsWith("pods"));
  }
});

test("pods stay a bar, coloured by readiness alone", () => {
  assert.equal(podsFace(2, 2, 0).image, bar(BRAND.aqua));
  assert.equal(podsFace(1, 2, 0).image, bar(BRAND.gold));
  assert.equal(podsFace(0, 2, 0).image, bar(BRAND.coral));
  // Restarts are a caveat in the label, not a change of state.
  assert.equal(podsFace(2, 2, 5).image, bar(BRAND.aqua));
});
