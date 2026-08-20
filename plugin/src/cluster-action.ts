// plugin/src/cluster-action.ts
import { action, SingletonAction, WillAppearEvent, WillDisappearEvent } from "@elgato/streamdeck";
import { trace } from "./trace.js";

interface ClusterSettings {
  metric: string;
  kromgo_url: string;
  label: string;
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

    await this.poll(ev.action, s.metric, s.kromgo_url, s.label);
    const timer = setInterval(
      () => this.poll(ev.action, s.metric, s.kromgo_url, s.label),
      POLL_INTERVAL_MS,
    );
    this.timers.set(ev.action.id, timer);
  }

  override onWillDisappear(ev: WillDisappearEvent): void {
    const timer = this.timers.get(ev.action.id);
    if (timer) {
      clearInterval(timer);
      this.timers.delete(ev.action.id);
    }
  }

  private async poll(
    act: { setTitle(t: string): Promise<void>; setImage(img: string): Promise<void> },
    metric: string,
    kromgo_url: string,
    label: string,
  ): Promise<void> {
    try {
      const url = `${kromgo_url}/badges/${metric}?format=json`;
      trace(`poll ${url}`);
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json() as KromgoResponse;
      trace(`ok ${metric} = ${data.value}`);
      await act.setTitle(`${label}\n${data.value}`);
      const hex = COLOR_MAP[data.color] ?? COLOR_MAP["grey"];
      await act.setImage(coloredDot(hex!));
    } catch (err) {
      trace(`FAILED ${metric}: ${String(err)}`);
      await act.setTitle(`${label}\n?`);
      await act.setImage(coloredDot(COLOR_MAP["grey"]!));
    }
  }
}

function coloredDot(color: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144">
    <rect width="144" height="144" fill="#1a1a1a"/>
    <circle cx="72" cy="72" r="28" fill="${color}"/>
  </svg>`;
  // charset=utf8 with the markup inline, NOT base64. Stream Deck accepts
  // base64 for raster formats (PNG, JPEG) but not for SVG: given
  // "data:image/svg+xml;base64,..." it silently draws nothing and setImage
  // still resolves, so the key keeps whatever was under it and the failure
  // looks like the image simply not rendering.
  return `data:image/svg+xml;charset=utf8,${encodeURIComponent(svg)}`;
}
