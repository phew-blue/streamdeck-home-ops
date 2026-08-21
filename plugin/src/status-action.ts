// plugin/src/status-action.ts
import {
  action,
  SingletonAction,
  WillAppearEvent,
  WillDisappearEvent,
  KeyDownEvent,
} from "@elgato/streamdeck";
import type { StatusSettings } from "./types.js";
import { getPodStatus, getCpuUsage, getRamUsage } from "./kubectl.js";
import { bar, gauge, BRAND, band } from "./tile.js";
import { paint, keepPainted, stopPainting } from "./paint.js";

const POLL_INTERVAL_MS = 30_000;

@action({ UUID: "com.phew.blue.homeops.status" })
export class StatusAction extends SingletonAction {
  private timers = new Map<string, ReturnType<typeof setInterval>>();

  override async onWillAppear(ev: WillAppearEvent): Promise<void> {
    const { action, payload } = ev;
    const s = payload.settings as unknown as StatusSettings;
    if (!s.app || !s.namespace) return;

    const id = action.id;
    await this.poll(id, action, s.app, s.namespace, s.deployment, s.metric);
    // Stream Deck drops a plugin-set image whenever it redraws a key, so the
    // artwork is reapplied between the slower data refreshes.
    keepPainted(id, action);
    const timer = setInterval(
      () => this.poll(id, action, s.app, s.namespace, s.deployment, s.metric),
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

  override async onKeyDown(ev: KeyDownEvent): Promise<void> {
    const s = ev.payload.settings as unknown as StatusSettings;
    if (s.app && s.namespace) {
    }
  }

  private async poll(
    id: string,
    act: { setTitle(t: string): Promise<void>; setImage(img: string): Promise<void> },
    app: string,
    namespace: string,
    deployment: string,
    metric: "pods" | "cpu" | "ram",
  ): Promise<void> {
    try {
      if (metric === "pods") {
        const status = await getPodStatus(deployment, namespace);
        const accent = status.ready === 0 ? BRAND.coral
          : status.ready < status.desired ? BRAND.gold
          : BRAND.aqua;
        // Restarts ride in the label rather than the value: they are a caveat
        // on the number, not the number itself, and they are usually zero.
        const label = status.restarts > 0 ? `${status.restarts}r` : "pods";
        await paint(id, act, `${label}\n${status.ready}/${status.desired}`, bar(accent));
      } else {
        const usage = metric === "cpu"
          ? await getCpuUsage(deployment, namespace)
          : await getRamUsage(deployment, namespace);
        const unit = metric === "cpu" ? "m" : "Mi";
        // A dial only where a limit exists to divide by. Without one there is
        // no ceiling, so the plain figure is the honest thing to show.
        if (usage.limit > 0) {
          const pct = usage.used / usage.limit;
          await paint(id, act, `${metric.toUpperCase()}\n${Math.round(pct * 100)}%`, gauge(band(pct * 100), pct));
        } else {
          await paint(id, act, `${metric.toUpperCase()}\n${usage.used}${unit}`, bar(BRAND.sky));
        }
      }
    } catch {
await paint(id, act, `${metric.toUpperCase()}\n?`, bar(BRAND.grey));
    }
  }
}

function coloredCircle(color: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144">
    <circle cx="72" cy="72" r="60" fill="${color}" opacity="0.3"/>
    <circle cx="72" cy="72" r="20" fill="${color}"/>
  </svg>`;
  // The raw SVG markup, which is what setImage documents it takes ("a base64
  // encoded string with the mime type declared, or an SVG string"). The
  // previous form was "data:image/svg+xml;base64,...", and Stream Deck accepts
  // base64 only for raster formats -- given base64 SVG it draws nothing while
  // setImage still resolves, so the key keeps whatever was under it.
  return svg;
}
