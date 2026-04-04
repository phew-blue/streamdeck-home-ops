// plugin/src/node-action.ts
import {
  action, SingletonAction,
  WillAppearEvent, WillDisappearEvent, KeyDownEvent,
} from "@elgato/streamdeck";
import { exec } from "node:child_process";
import { promisify } from "node:util";

const execAsync = promisify(exec);
const POLL_MS = 30_000;

interface NodeSettings {
  node: string;
  role: string;
  metric: "node" | "pods" | "cpu" | "ram";
}

async function run(cmd: string): Promise<string> {
  try {
    const { stdout } = await execAsync(cmd, { timeout: 10000 });
    return stdout.trim();
  } catch { return ""; }
}

@action({ UUID: "com.phewblue.homeops.node" })
export class NodeAction extends SingletonAction {
  private timers = new Map<string, ReturnType<typeof setInterval>>();

  override async onWillAppear(ev: WillAppearEvent): Promise<void> {
    const s = ev.payload.settings as unknown as NodeSettings;
    if (!s.node) return;
    await this.poll(ev.action, s.node, s.role, s.metric);
    const timer = setInterval(() => this.poll(ev.action, s.node, s.role, s.metric), POLL_MS);
    this.timers.set(ev.action.id, timer);
  }

  override onWillDisappear(ev: WillDisappearEvent): void {
    const t = this.timers.get(ev.action.id);
    if (t) { clearInterval(t); this.timers.delete(ev.action.id); }
  }

  override async onKeyDown(ev: KeyDownEvent): Promise<void> {
    const s = ev.payload.settings as unknown as NodeSettings;
    if (s.metric === "node") {
      exec(`start cmd /k kubectl describe node ${s.node}`);
    }
  }

  private async poll(
    act: { setTitle(t: string): Promise<void>; setImage(img: string): Promise<void> },
    node: string,
    role: string,
    metric: NodeSettings["metric"],
  ): Promise<void> {
    try {
      const ready = await getNodeReady(node);
      const readyColor = ready ? "#2e7d32" : "#c62828";

      if (metric === "node") {
        const label = role === "control-plane" ? "CP" : "W";
        await act.setTitle(`${node}\n${label}`);
        await act.setImage(dot(readyColor));
      } else if (metric === "pods") {
        const { running, capacity } = await getNodePods(node);
        const pct = capacity > 0 ? running / capacity : 0;
        const color = pct > 0.8 ? "#c62828" : pct > 0.5 ? "#e65100" : "#2e7d32";
        await act.setTitle(`${running}/${capacity}\npods`);
        await act.setImage(dot(color));
      } else {
        const { cpu, ram } = await getNodeResources(node);
        if (metric === "cpu") {
          const color = cpu > 80 ? "#c62828" : cpu > 50 ? "#e65100" : "#2e7d32";
          await act.setTitle(`CPU\n${cpu}%`);
          await act.setImage(dot(color));
        } else {
          const color = ram > 80 ? "#c62828" : ram > 50 ? "#e65100" : "#2e7d32";
          await act.setTitle(`RAM\n${ram}%`);
          await act.setImage(dot(color));
        }
      }
    } catch {
      await act.setTitle("ERR");
    }
  }
}

async function getNodeReady(node: string): Promise<boolean> {
  const out = await run(
    `kubectl get node ${node} -o jsonpath="{.status.conditions[?(@.type=='Ready')].status}"`
  );
  return out === "True";
}

async function getNodePods(node: string): Promise<{ running: number; capacity: number }> {
  const [runningOut, capacityOut] = await Promise.all([
    run(`kubectl get pods -A --field-selector spec.nodeName=${node},status.phase=Running --no-headers 2>/dev/null | wc -l`),
    run(`kubectl get node ${node} -o jsonpath="{.status.allocatable.pods}"`),
  ]);
  return {
    running: parseInt(runningOut.trim(), 10) || 0,
    capacity: parseInt(capacityOut.trim(), 10) || 110,
  };
}

async function getNodeResources(node: string): Promise<{ cpu: number; ram: number }> {
  const out = await run(`kubectl top node ${node} --no-headers`);
  const match = out.match(/\S+\s+\S+\s+(\d+)%\s+\S+\s+(\d+)%/);
  return {
    cpu: match ? parseInt(match[1], 10) : 0,
    ram: match ? parseInt(match[2], 10) : 0,
  };
}

function dot(color: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144">
    <rect width="144" height="144" fill="#1a1a1a"/>
    <circle cx="72" cy="72" r="28" fill="${color}"/>
  </svg>`;
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
}
