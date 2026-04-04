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

const POLL_INTERVAL_MS = 30_000;

@action({ UUID: "com.phewblue.homeops.status" })
export class StatusAction extends SingletonAction {
  private timers = new Map<string, ReturnType<typeof setInterval>>();

  override async onWillAppear(ev: WillAppearEvent): Promise<void> {
    const { action, payload } = ev;
    const s = payload.settings as unknown as StatusSettings;
    if (!s.app || !s.namespace) return;

    await this.poll(action, s.app, s.namespace, s.deployment, s.metric);
    const timer = setInterval(
      () => this.poll(action, s.app, s.namespace, s.deployment, s.metric),
      POLL_INTERVAL_MS,
    );
    this.timers.set(action.id, timer);
  }

  override onWillDisappear(ev: WillDisappearEvent): void {
    const timer = this.timers.get(ev.action.id);
    if (timer) {
      clearInterval(timer);
      this.timers.delete(ev.action.id);
    }
  }

  override async onKeyDown(ev: KeyDownEvent): Promise<void> {
    const s = ev.payload.settings as unknown as StatusSettings;
    if (s.app && s.namespace) {
      await this.poll(ev.action, s.app, s.namespace, s.deployment, s.metric);
    }
  }

  private async poll(
    act: { setTitle(t: string): Promise<void>; setImage(img: string): Promise<void> },
    app: string,
    namespace: string,
    deployment: string,
    metric: "pods" | "cpu" | "ram",
  ): Promise<void> {
    try {
      if (metric === "pods") {
        const status = await getPodStatus(deployment, namespace);
        const title = `${status.ready}/${status.desired} · ${status.restarts}↺`;
        const color = status.ready === 0 ? "#c62828"
          : status.ready < status.desired ? "#e65100"
          : "#2e7d32";
        await act.setTitle(title);
        await act.setImage(coloredCircle(color));
      } else if (metric === "cpu") {
        const usage = await getCpuUsage(deployment, namespace);
        const pct = usage.limit > 0 ? usage.used / usage.limit : 0;
        const title = usage.limit > 0 ? `${usage.used}m/${usage.limit}m` : `${usage.used}m`;
        const color = pct > 0.8 ? "#c62828" : pct > 0.5 ? "#e65100" : "#2e7d32";
        await act.setTitle(`CPU\n${title}`);
        await act.setImage(coloredCircle(color));
      } else if (metric === "ram") {
        const usage = await getRamUsage(deployment, namespace);
        const pct = usage.limit > 0 ? usage.used / usage.limit : 0;
        const title = usage.limit > 0 ? `${usage.used}/${usage.limit}Mi` : `${usage.used}Mi`;
        const color = pct > 0.8 ? "#c62828" : pct > 0.5 ? "#e65100" : "#2e7d32";
        await act.setTitle(`RAM\n${title}`);
        await act.setImage(coloredCircle(color));
      }
    } catch {
      await act.setTitle("ERR");
    }
  }
}

function coloredCircle(color: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144">
    <circle cx="72" cy="72" r="60" fill="${color}" opacity="0.3"/>
    <circle cx="72" cy="72" r="20" fill="${color}"/>
  </svg>`;
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
}
