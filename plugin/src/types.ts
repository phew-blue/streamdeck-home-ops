// plugin/src/types.ts

export interface StatusSettings {
  app: string;
  namespace: string;
  deployment: string;
  metric: "pods" | "cpu" | "ram";
}

export interface PodStatus {
  ready: number;
  desired: number;
  restarts: number;
}

export interface ResourceUsage {
  used: number;
  limit: number;
  unit: "m" | "Mi";
}

export type HelmReleaseState = "Ready" | "Failed" | "Progressing" | "Unknown";
