"use client"

import { Activity, RefreshCw, ShieldCheck } from "lucide-react"

interface HeaderProps {
    windowDays: number;
    onWindowChange: (days: number) => void;
    apiHealthy: boolean | null;
    isLoading: boolean;
    onRefresh: () => void;
}

const WINDOW_OPTIONS = [30, 60, 90, 120];

export function Header({
  windowDays,
  onWindowChange,
  apiHealthy,
  isLoading,
  onRefresh,
}: HeaderProps) {
    return (
        <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold tracking-tight text-white">
                QA Metrics Dashboard
              </h1>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                QA-GOV-2026-v1.0
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Strategic Engineering Quality Governance &amp; Test Telemetry
            </p>
          </div>
        </div>
        {}
        <div className="flex items-center gap-3 self-start sm:self-auto">
          {}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
              apiHealthy === null
                ? "bg-slate-800/50 text-slate-400 border-slate-700"
                : apiHealthy
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-rose-500/10 text-rose-400 border-rose-500/20"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>
              {apiHealthy === null
                ? "Checking API..."
                : apiHealthy
                ? "API Online"
                : "API Offline"}
            </span>
          </div>
          {/* Time Window Segmented Control */}
          <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800">
            {WINDOW_OPTIONS.map((days) => {
              const active = windowDays === days;
              return (
                <button
                  key={days}
                  onClick={() => onWindowChange(days)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                    active
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {days}d
                </button>
              );
            })}
          </div>
          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh metrics"
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`}
            />
          </button>
        </div>
      </div>
    </header>
  );
}