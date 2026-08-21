// plugin/src/node-action.ts
import {
  action, SingletonAction,
  WillAppearEvent, WillDisappearEvent, KeyDownEvent,
} from "@elgato/streamdeck";
import { exec } from "node:child_process";

import { bar, gauge, BRAND, band } from "./tile.js";
import { snapshot } from "./snapshot.js";
import { paint, keepPainted, stopPainting } from "./paint.js";

const POLL_MS = 30_000;

interface NodeSettings {
  node: string;
  role: string;
  metric: "node" | "pods" | "cpu" | "ram";
}

@action({ UUID: "com.phew.blue.homeops.node" })
export class NodeAction extends SingletonAction {
  private timers = new Map<string, ReturnType<typeof setInterval>>();

  override async onWillAppear(ev: WillAppearEvent): Promise<void> {
    const s = ev.payload.settings as unknown as NodeSettings;
    if (!s.node) return;
    const id = ev.action.id;
    await this.poll(id, ev.action, s.node, s.role, s.metric);
    // Stream Deck drops a plugin-set image whenever it redraws a key, so the
    // artwork is reapplied between the slower data refreshes.
    keepPainted(id, ev.action);
    const timer = setInterval(() => this.poll(id, ev.action, s.node, s.role, s.metric), POLL_MS);
    this.timers.set(id, timer);
  }

  override onWillDisappear(ev: WillDisappearEvent): void {
    stopPainting(ev.action.id);
    const t = this.timers.get(ev.action.id);
    if (t) { clearInterval(t); this.timers.delete(ev.action.id); }
  }

  override async onKeyDown(ev: KeyDownEvent): Promise<void> {
    const s = ev.payload.settings as unknown as NodeSettings;
    if (s.metric === "node") {
      // windowsHide is deliberately NOT set: this one is meant to open a window.
      exec(`start cmd /k kubectl describe node ${s.node}`);
    }
  }

  private async poll(
    id: string,
    act: { setTitle(t: string): Promise<void>; setImage(img: string): Promise<void> },
    node: string,
    role: string,
    metric: NodeSettings["metric"],
  ): Promise<void> {
    try {
      // Every node tile reads the one shared snapshot rather than running its
      // own kubectl. See snapshot.ts for what the per-tile version cost.
      const info = (await snapshot()).nodes.get(node);
      if (!info) {
        await paint(id, act, `${node}\n?`, bar(BRAND.grey));
        return;
      }
      if (metric === "node") {
        const kind = role === "control-plane" ? "CP" : "W";
        await paint(id, act, `${node}\n${kind}`, bar(info.ready ? BRAND.aqua : BRAND.coral));
      } else if (metric === "pods") {
        const pct = info.podCapacity > 0 ? (info.podsRunning / info.podCapacity) * 100 : 0;
        await paint(id, act, `pods\n${info.podsRunning}/${info.podCapacity}`, bar(band(pct)));
      } else {
        const v = metric === "cpu" ? info.cpuPct : info.ramPct;
        await paint(id, act, `${metric.toUpperCase()}\n${v}%`, gauge(band(v), v / 100));
      }
    } catch {
      await paint(id, act, `${metric === "node" ? node : metric}\n?`, bar(BRAND.grey));
    }
  }
}
