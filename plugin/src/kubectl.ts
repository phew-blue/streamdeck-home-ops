// plugin/src/kubectl.ts
//
// App-level readings, served from the shared cluster snapshot.
//
// These used to be six kubectl invocations per tile per thirty seconds, run
// independently by every tile on the page. See snapshot.ts for what that cost
// and why it is now a handful of cluster-wide calls behind a cache.
import { snapshot } from "./snapshot.js";
import type { PodStatus, ResourceUsage } from "./types.js";

export async function getPodStatus(deployment: string, namespace: string): Promise<PodStatus> {
  const a = (await snapshot()).apps.get(`${namespace}/${deployment}`);
  return a
    ? { ready: a.ready, desired: a.desired, restarts: a.restarts }
    : { ready: 0, desired: 0, restarts: 0 };
}

export async function getCpuUsage(deployment: string, namespace: string): Promise<ResourceUsage> {
  const a = (await snapshot()).apps.get(`${namespace}/${deployment}`);
  return { used: a?.cpuUsed ?? 0, limit: a?.cpuLimit ?? 0, unit: "m" };
}

export async function getRamUsage(deployment: string, namespace: string): Promise<ResourceUsage> {
  const a = (await snapshot()).apps.get(`${namespace}/${deployment}`);
  return { used: a?.ramUsed ?? 0, limit: a?.ramLimit ?? 0, unit: "Mi" };
}
