"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";
import {
  checkApiHealth,
  fetchBoardTickets,
  fetchDashboardHeatmap,
  fetchDashboardKPIs,
  fetchQuarantineCandidates,
} from "@/lib/api";
import {
  BoardTicket,
  DashboardKPIsResponse,
  HeatmapResponse,
  QuarantineCandidate,
} from "@/types/api";
import { Header } from "@/components/Header";
import { KpiGrid } from "@/components/KpiGrid";
import { RiskHeatmap } from "@/components/RiskHeatmap";
import { QuarantineTable } from "@/components/QuarantineTable";
import { BoardExplorer } from "@/components/BoardExplorer";

export default function DashboardPage() {
  const [windowDays, setWindowDays] = useState<number>(60);
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [kpis, setKpis] = useState<DashboardKPIsResponse | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [quarantine, setQuarantine] = useState<QuarantineCandidate[]>([]);
  const [tickets, setTickets] = useState<BoardTicket[]>([]);

  const loadDashboardData = useCallback(async (days: number) => {
    setIsLoading(true);
    setError(null);

    const healthy = await checkApiHealth();
    setApiHealthy(healthy);

    if (!healthy) {
      setError(
        "Cannot reach FastAPI backend at http://localhost:8000. Make sure uvicorn is running."
      );
      setIsLoading(false);
      return;
    }

    try {
      const [kpisData, heatmapData, quarantineData, ticketsData] =
        await Promise.all([
          fetchDashboardKPIs(days),
          fetchDashboardHeatmap(days),
          fetchQuarantineCandidates(days),
          fetchBoardTickets(25),
        ]);

      setKpis(kpisData);
      setHeatmap(heatmapData);
      setQuarantine(quarantineData);
      setTickets(ticketsData);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load telemetry data."
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData(windowDays);
  }, [windowDays, loadDashboardData]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header
        windowDays={windowDays}
        onWindowChange={setWindowDays}
        apiHealthy={apiHealthy}
        isLoading={isLoading}
        onRefresh={() => loadDashboardData(windowDays)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {error && (
          <div className="rounded-xl bg-rose-500/10 border border-rose-500/30 p-4 flex items-center gap-3 text-rose-300 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <div>
              <p className="font-semibold">Backend Connection Error</p>
              <p className="text-xs text-rose-300/80 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {isLoading && !kpis ? (
          <div className="space-y-6 animate-pulse">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <div
                  key={i}
                  className="h-36 rounded-xl bg-slate-900 border border-slate-800"
                />
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="h-80 rounded-xl bg-slate-900 border border-slate-800" />
              <div className="h-80 rounded-xl bg-slate-900 border border-slate-800" />
            </div>
          </div>
        ) : (
          kpis &&
          heatmap && (
            <>
              <KpiGrid data={kpis} />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <RiskHeatmap heatmap={heatmap} />
                <QuarantineTable candidates={quarantine} />
              </div>

              <BoardExplorer
                tickets={tickets}
                onSyncComplete={() => loadDashboardData(windowDays)}
              />
            </>
          )
        )}
      </main>
    </div>
  );
}