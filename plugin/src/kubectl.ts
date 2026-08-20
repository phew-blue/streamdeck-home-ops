// plugin/src/kubectl.ts
import { exec } from "node:child_process";
import { promisify } from "node:util";
import type { PodStatus, ResourceUsage, HelmReleaseState } from "./types.js";

const execAsync = promisify(exec);

// How long a single kubectl invocation may take before it is abandoned.
const EXEC_TIMEOUT_MS = 10_000;

async function run(cmd: string): Promise<string> {
  try {
    const { stdout } = await execAsync(cmd, {
      timeout: EXEC_TIMEOUT_MS,
      // windowsHide defaults to FALSE. Without it every invocation flashes a
      // console window on the user's desktop -- and because exec() goes via
      // cmd.exe, that happens even when kubectl is not installed and the
      // command fails instantly. On a machine running a fullscreen game those
      // windows steal focus, which is how this was found: it was pulling the
      // user out of a match every thirty seconds.
      windowsHide: true,
    });
    return stdout.trim();
  } catch {
    return "";
  }
}

export async function getPodStatus(deployment: string, namespace: string): Promise<PodStatus> {
  const [readyOut, restartOut] = await Promise.all([
    run(`kubectl get deployment ${deployment} -n ${namespace} -o jsonpath="{.status.readyReplicas}/{.spec.replicas}"`),
    run(`kubectl get pods -n ${namespace} -l app.kubernetes.io/name=${deployment} -o jsonpath="{.items[*].status.containerStatuses[*].restartCount}"`),
  ]);

  const parts = readyOut.split("/");
  const ready = parseInt(parts[0] ?? "0", 10) || 0;
  const desired = parseInt(parts[1] ?? "0", 10) || 0;

  const restartNums = restartOut.split(" ").map(Number).filter(n => !isNaN(n));
  const restarts = restartNums.reduce((sum, n) => sum + n, 0);

  return { ready, desired, restarts };
}

export async function getCpuUsage(deployment: string, namespace: string): Promise<ResourceUsage> {
  const topOut = await run(
    `kubectl top pod -n ${namespace} -l app.kubernetes.io/name=${deployment} --no-headers --sum`
  );
  const lines = topOut.split("\n").filter(Boolean);
  const sumLine = lines[lines.length - 1] ?? "";
  const match = sumLine.match(/(\d+)m\s+(\d+)Mi/);
  const used = match ? parseInt(match[1], 10) : 0;

  const limitOut = await run(
    `kubectl get deployment ${deployment} -n ${namespace} -o jsonpath="{.spec.template.spec.containers[0].resources.limits.cpu}"`
  );
  const limitStr = limitOut.replace("m", "");
  const limit = limitStr ? parseInt(limitStr, 10) : 0;

  return { used, limit, unit: "m" };
}

export async function getRamUsage(deployment: string, namespace: string): Promise<ResourceUsage> {
  const topOut = await run(
    `kubectl top pod -n ${namespace} -l app.kubernetes.io/name=${deployment} --no-headers --sum`
  );
  const lines = topOut.split("\n").filter(Boolean);
  const sumLine = lines[lines.length - 1] ?? "";
  const match = sumLine.match(/(\d+)m\s+(\d+)Mi/);
  const used = match ? parseInt(match[2], 10) : 0;

  const limitOut = await run(
    `kubectl get deployment ${deployment} -n ${namespace} -o jsonpath="{.spec.template.spec.containers[0].resources.limits.memory}"`
  );
  let limit = 0;
  if (limitOut.includes("Gi")) {
    limit = Math.round(parseFloat(limitOut) * 1024);
  } else if (limitOut.includes("Mi")) {
    limit = parseInt(limitOut, 10);
  }

  return { used, limit, unit: "Mi" };
}

export async function getHelmReleaseState(app: string, namespace: string): Promise<HelmReleaseState> {
  const out = await run(`flux get hr ${app} -n ${namespace} --no-header`);
  if (!out) return "Unknown";
  if (out.includes("True")) return "Ready";
  if (out.includes("False")) return "Failed";
  if (out.includes("progressing") || out.includes("Progressing")) return "Progressing";
  return "Unknown";
}
