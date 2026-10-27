import {
  DashboardKPIsResponse,
  HeatmapResponse,
  QuarantineCandidate,
} from "@/types/api";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export async function checkApiHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, {
      cache: "no-store",
    });
    return res.ok;
  } catch {
    return false;
  }
}
export async function fetchDashboardKPIs(
  windowDays: number = 60
): Promise<DashboardKPIsResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/metrics/kpis?window_days=${windowDays}`,
    { cache: "no-store" }
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch KPIs: ${res.status}`);
  }
  return res.json();
}
export async function fetchDashboardHeatmap(
  windowDays: number = 60
): Promise<HeatmapResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/metrics/heatmap?window_days=${windowDays}`,
    { cache: "no-store" }
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch Heatmap: ${res.status}`);
  }
  return res.json();
}
export async function fetchQuarantineCandidates(
  windowDays: number = 60
): Promise<QuarantineCandidate[]> {
  const res = await fetch(
    `${API_BASE_URL}/api/metrics/quarantine?window_days=${windowDays}`,
    { cache: "no-store" }
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch Quarantine list: ${res.status}`);
  }
  return res.json();
}