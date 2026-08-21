// plugin/src/snapshot.ts
//
// One view of the cluster, shared by every tile.
//
// # Why this exists
//
// Each tile used to run its own kubectl: a node tile made five calls, an app
// tile six, every thirty seconds, independently. On a page of twenty-odd tiles
// that measured 69 processes in 35 seconds, peaking at 29 concurrent copies of
// a 61MB binary -- enough to give a machine running a game visible lag spikes,
// which is exactly what it did.
//
// The data is cluster-wide anyway, so it is fetched cluster-wide: a handful of
// calls behind a TTL cache, and every tile reads from that. Twenty tiles now
// cost the same as one.
//
// Output formats are chosen to stay small. `-o json` for pods on a 400-pod
// cluster is megabytes to serialise and parse; custom-columns is a few KB.
import { exec } from "node:child_process";
import { promisify } from "node:util";
import { trace } from "./trace.js";

const execAsync = promisify(exec);

/**
 * Where to find kubectl.
 *
 * Not simply "kubectl": Stream Deck is started by Task Scheduler, which hands
 * its children an environment block captured earlier, so a PATH entry added
 * afterwards is invisible to the plugin however correct it looks in a shell.
 * That produced a page of "?" tiles with nothing wrong anywhere else.
 *
 * The candidates are tried once and the winner remembered.
 */
const CANDIDATES = [
  "kubectl",
  "C:\\Users\\Public\\bin\\kubectl.exe",
  "C:\\Program Files\\kubectl\\kubectl.exe",
];

let kubectlCmd: string | null = null;

async function resolveKubectl(): Promise<string | null> {
  if (kubectlCmd) return kubectlCmd;
  for (const c of CANDIDATES) {
    const quoted = c.includes(" ") ? `"${c}"` : c;
    try {
      await execAsync(`${quoted} version --client=true -o json`, {
        timeout: 10_000, windowsHide: true,
      });
      kubectlCmd = quoted;
      trace(`kubectl found: ${c}`);
      return kubectlCmd;
    } catch {
      // Try the next one; only the absence of all of them is worth reporting.
    }
  }
  trace(`kubectl not found; tried ${CANDIDATES.join(", ")}`);
  return null;
}

/** How long a snapshot is reused. Matches the tiles' own refresh rate. */
const TTL_MS = 30_000;

/** A slow kubectl must not wedge the cache; the next tick tries again. */
const EXEC_TIMEOUT_MS = 15_000;

async function run(args: string): Promise<string> {
  const bin = await resolveKubectl();
  if (!bin) return "";
  const cmd = `${bin} ${args}`;
  try {
    const { stdout } = await execAsync(cmd, {
      timeout: EXEC_TIMEOUT_MS,
      maxBuffer: 8 * 1024 * 1024,
      // Without this every call flashes a console window on the desktop -- and
      // because exec goes via cmd.exe it happens even when kubectl is absent.
      windowsHide: true,
    });
    return stdout.trim();
  } catch (err) {
    trace(`kubectl failed: ${cmd.slice(0, 60)}... ${String(err).slice(0, 120)}`);
    return "";
  }
}

export interface NodeInfo {
  ready: boolean;
  podCapacity: number;
  podsRunning: number;
  cpuPct: number;
  ramPct: number;
}

export interface AppInfo {
  ready: number;
  desired: number;
  restarts: number;
  cpuUsed: number;   // millicores
  cpuLimit: number;
  ramUsed: number;   // MiB
  ramLimit: number;
}

export interface Snapshot {
  nodes: Map<string, NodeInfo>;
  apps: Map<string, AppInfo>;   // keyed "namespace/deployment"
  ok: boolean;
}

let cached: Snapshot | null = null;
let cachedAt = 0;
let inflight: Promise<Snapshot> | null = null;

/**
 * The current view, fetched at most once per TTL.
 *
 * Concurrent callers share one fetch: twenty tiles appearing at once must not
 * become twenty kubectl storms, which is the whole point of this file.
 */
export function snapshot(): Promise<Snapshot> {
  const now = Date.now();
  if (cached && now - cachedAt < TTL_MS) return Promise.resolve(cached);
  if (inflight) return inflight;
  inflight = collect().then((s) => {
    cached = s;
    cachedAt = Date.now();
    inflight = null;
    return s;
  }).catch((e) => {
    inflight = null;
    throw e;
  });
  return inflight;
}

/** "1500m" / "1.5" -> millicores; "" -> 0. */
function millicores(v: string): number {
  if (!v) return 0;
  if (v.endsWith("m")) return parseInt(v, 10) || 0;
  const n = parseFloat(v);
  return Number.isFinite(n) ? Math.round(n * 1000) : 0;
}

/** "512Mi" / "1Gi" / "1048576Ki" -> MiB; "" -> 0. */
function mib(v: string): number {
  if (!v) return 0;
  const m = /^(\d+(?:\.\d+)?)([EPTGMK]i?)?$/.exec(v);
  if (!m) return 0;
  const n = parseFloat(m[1]!);
  switch (m[2]) {
    case "Gi": return Math.round(n * 1024);
    case "Mi": return Math.round(n);
    case "Ki": return Math.round(n / 1024);
    case "G": return Math.round((n * 1e9) / (1024 * 1024));
    case "M": return Math.round((n * 1e6) / (1024 * 1024));
    default: return Math.round(n / (1024 * 1024));
  }
}

function rows(out: string): string[][] {
  return out.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => l.split(/\s+/));
}

async function collect(): Promise<Snapshot> {
  const nodes = new Map<string, NodeInfo>();
  const apps = new Map<string, AppInfo>();

  // Six calls, whatever the page holds.
  const [nodeStatus, nodeCap, nodeTop, podOut, deployOut, podTop] = await Promise.all([
    // Two plain queries rather than one with a jsonpath filter: the filter
    // needs inner double quotes ( [?(@.type=="Ready")] ) and exec goes through
    // cmd.exe, which eats them -- the call failed with nothing but a truncated
    // error while every other query worked.
    run("get nodes --no-headers"),
    run("get nodes --no-headers -o custom-columns=N:.metadata.name,P:.status.allocatable.pods"),
    run("top nodes --no-headers"),
    run('get pods -A --no-headers -o custom-columns=' +
        "NODE:.spec.nodeName,PHASE:.status.phase,NS:.metadata.namespace," +
        "APP:.metadata.labels.app\\.kubernetes\\.io/name,RS:.status.containerStatuses[*].restartCount"),
    run('get deploy -A --no-headers -o custom-columns=' +
        "NS:.metadata.namespace,NAME:.metadata.name,RDY:.status.readyReplicas,DES:.spec.replicas," +
        "CPU:.spec.template.spec.containers[0].resources.limits.cpu," +
        "MEM:.spec.template.spec.containers[0].resources.limits.memory"),
    run("top pod -A --no-headers"),
  ]);

  const ok = nodeStatus !== "";

  // `kubectl get nodes` prints NAME STATUS ROLES AGE VERSION.
  for (const [name, status] of rows(nodeStatus)) {
    nodes.set(name!, {
      ready: status === "Ready",
      podCapacity: 0, podsRunning: 0, cpuPct: 0, ramPct: 0,
    });
  }
  for (const [name, cap] of rows(nodeCap)) {
    const n = nodes.get(name!);
    if (n) n.podCapacity = parseInt(cap ?? "0", 10) || 0;
  }
  // kubectl top nodes: NAME CPU(cores) CPU% MEM(bytes) MEM%
  for (const r of rows(nodeTop)) {
    const n = nodes.get(r[0]!);
    if (n) {
      n.cpuPct = parseInt((r[2] ?? "").replace("%", ""), 10) || 0;
      n.ramPct = parseInt((r[4] ?? "").replace("%", ""), 10) || 0;
    }
  }

  // Pods give both the per-node running count and per-app restart totals.
  const restarts = new Map<string, number>();
  for (const [node, phase, ns, app, rs] of rows(podOut)) {
    if (phase === "Running") {
      const n = nodes.get(node!);
      if (n) n.podsRunning++;
    }
    if (app && app !== "<none>") {
      const key = `${ns}/${app}`;
      const total = (rs ?? "").split(",").reduce((s, v) => s + (parseInt(v, 10) || 0), 0);
      restarts.set(key, (restarts.get(key) ?? 0) + total);
    }
  }

  for (const [ns, name, rdy, des, cpu, mem] of rows(deployOut)) {
    const key = `${ns}/${name}`;
    apps.set(key, {
      ready: parseInt(rdy ?? "0", 10) || 0,
      desired: parseInt(des ?? "0", 10) || 0,
      restarts: restarts.get(key) ?? 0,
      cpuUsed: 0,
      cpuLimit: millicores(cpu === "<none>" ? "" : cpu ?? ""),
      ramUsed: 0,
      ramLimit: mib(mem === "<none>" ? "" : mem ?? ""),
    });
  }

  // kubectl top pod -A: NAMESPACE NAME CPU MEM. Pod names carry the deployment
  // name as a prefix, so usage is attributed by longest matching app key --
  // exact enough for a tile, and it needs no extra call.
  const keys = [...apps.keys()];
  for (const [ns, pod, cpu, mem] of rows(podTop)) {
    let best = "";
    for (const k of keys) {
      if (!k.startsWith(`${ns}/`)) continue;
      const dep = k.slice(ns!.length + 1);
      if (pod!.startsWith(dep) && dep.length > best.length) best = dep;
    }
    if (!best) continue;
    const a = apps.get(`${ns}/${best}`)!;
    a.cpuUsed += millicores(cpu ?? "");
    a.ramUsed += mib(mem ?? "");
  }

  trace(`snapshot: ${nodes.size} nodes, ${apps.size} apps, ok=${ok}`);
  return { nodes, apps, ok };
}
