// plugin/src/cluster-action.ts
import { action, SingletonAction, WillAppearEvent, WillDisappearEvent } from "@elgato/streamdeck";
import { trace } from "./trace.js";
import { paint, keepPainted, stopPainting } from "./paint.js";
import { forValue, bar, logo, accentFor, BRAND } from "./tile.js";
import { logoFor } from "./logos.js";

interface ClusterSettings {
  metric: string;
  kromgo_url: string;
  label: string;
  /**
   * Draw the product's mark instead of a label.
   *
   * Off by default. Talos and Kubernetes already have folder buttons carrying
   * their marks, so a version tile that repeats them puts the same logo on the
   * page twice; those read better as label-and-value like every other stat.
   * Flux has no folder button, so its tile is the only place its mark appears.
   */
  logo?: boolean;
}

// The response from kromgo's JSON endpoint.
//
// This is home-operations/kromgo, which is NOT the shields.io-shaped payload
// kashalls/kromgo served ({schemaVersion, label, message, color} straight off
// /<metric>). The project moved orgs and the API moved with it: badges now live
// under /badges/<id>, and asking for JSON gives the value in `value` rather
// than `message`. Reading the old field silently yields undefined, which is
// indistinguishable from the endpoint being down -- every tile just shows "?".
interface KromgoResponse {
  id: string;
  title: string;
  value: string;
  color: string;
  result: number;
}

const POLL_INTERVAL_MS = 5 * 60 * 1000;

const COLOR_MAP: Record<string, string> = {
  green:  "#2e7d32",
  orange: "#e65100",
  red:    "#c62828",
  blue:   "#1565c0",
  grey:   "#424242",
};

@action({ UUID: "com.phew.blue.homeops.cluster" })
export class ClusterAction extends SingletonAction {
  private timers = new Map<string, ReturnType<typeof setInterval>>();

  override async onWillAppear(ev: WillAppearEvent): Promise<void> {
    const s = ev.payload.settings as unknown as ClusterSettings;
    if (!s.metric || !s.kromgo_url) return;

    const id = ev.action.id;
    await this.poll(id, ev.action, s.metric, s.kromgo_url, s.label, s.logo === true);
    // Stream Deck drops a plugin-set image whenever it redraws the key, so the
    // artwork is put back on a short timer between the (much slower) fetches.
    keepPainted(id, ev.action);
    const timer = setInterval(
      () => this.poll(id, ev.action, s.metric, s.kromgo_url, s.label, s.logo === true),
      POLL_INTERVAL_MS,
    );
    this.timers.set(id, timer);
  }

  override onWillDisappear(ev: WillDisappearEvent): void {
    stopPainting(ev.action.id);
    const timer = this.timers.get(ev.action.id);
    if (timer) {
      clearInterval(timer);
      this.timers.delete(ev.action.id);
    }
  }

  private async poll(
    id: string,
    act: { setTitle(t: string): Promise<void>; setImage(img: string): Promise<void> },
    metric: string,
    kromgo_url: string,
    label: string,
    withLogo: boolean,
  ): Promise<void> {
    try {
      const url = `${kromgo_url}/badges/${metric}?format=json`;
      trace(`poll ${url}`);
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json() as KromgoResponse;
      trace(`ok ${metric} = ${data.value}`);
      // The tile draws the label and the value itself, so the deck's own title
      // is cleared -- leaving it set would print the value twice.
      // Title carries the reading, image carries the artwork. If Stream Deck
      // declines the SVG the numbers still show; the reverse loses everything.
      const accent = accentFor(data.color);
      const product = /^([a-z0-9]+)_version$/.exec(metric)?.[1];
      const mark = withLogo ? logoFor(metric) : undefined;
      await paint(id, act,
        mark ? data.value : `${label}\n${data.value}`,
        mark ? logo(product!, mark) : forValue(data.value, accent));
    } catch (err) {
      trace(`FAILED ${metric}: ${String(err)}`);
      await paint(id, act, `${label}\n?`, bar(BRAND.grey));
    }
  }
}

function coloredDot(color: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144">
    <rect width="144" height="144" fill="#1a1a1a"/>
    <circle cx="72" cy="72" r="28" fill="${color}"/>
  </svg>`;
  // The raw SVG markup, which is what setImage documents it takes ("a base64
  // encoded string with the mime type declared, or an SVG string"). The
  // previous form was "data:image/svg+xml;base64,...", and Stream Deck accepts
  // base64 only for raster formats -- given base64 SVG it draws nothing while
  // setImage still resolves, so the key keeps whatever was under it.
  return svg;
}
