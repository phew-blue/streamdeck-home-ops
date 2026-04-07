// plugin/src/cluster-action.ts
import { action, SingletonAction, WillAppearEvent, WillDisappearEvent } from "@elgato/streamdeck";

interface ClusterSettings {
  metric: string;
  kromgo_url: string;
  label: string;
}

interface KromgoResponse {
  schemaVersion: number;
  label: string;
  message: string;
  color: string;
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
      const resp = await fetch(`${kromgo_url}/${metric}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json() as KromgoResponse;
      await act.setTitle(`${label}\n${data.message}`);
      const hex = COLOR_MAP[data.color] ?? COLOR_MAP["grey"];
      await act.setImage(coloredDot(hex!));
    } catch {
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
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
}
