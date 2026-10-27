import React from "react";

export type KpiStatus = "healthy" | "warning" | "critical" | "neutral";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  sampleInfo?: string;
  status?: KpiStatus;
  statusLabel?: string;
  icon: React.ReactNode;
}

const STATUS_STYLES: Record<
  KpiStatus,
  { badge: string; border: string; iconBg: string }
> = {
  healthy: {
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    border: "border-slate-800 hover:border-emerald-500/40",
    iconBg: "bg-emerald-500/10 text-emerald-400",
  },
  warning: {
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    border: "border-slate-800 hover:border-amber-500/40",
    iconBg: "bg-amber-500/10 text-amber-400",
  },
  critical: {
    badge: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    border: "border-rose-500/30 hover:border-rose-500/60",
    iconBg: "bg-rose-500/10 text-rose-400",
  },
  neutral: {
    badge: "bg-slate-800 text-slate-300 border-slate-700",
    border: "border-slate-800 hover:border-slate-700",
    iconBg: "bg-indigo-500/10 text-indigo-400",
  },
};

export function KpiCard({
  title,
  value,
  subtitle,
  sampleInfo,
  status = "neutral",
  statusLabel,
  icon,
}: KpiCardProps) {
  const styles = STATUS_STYLES[status];
  return (
    <div
      className={`rounded-xl bg-slate-900/90 border p-5 transition-all shadow-sm flex flex-col justify-between ${styles.border}`}
    >
      <div>
        {/* Top Row: Title & Icon */}
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            {title}
          </span>
          <div className={`p-2 rounded-lg ${styles.iconBg}`}>{icon}</div>
        </div>
        {/* Middle Row: Primary Value & Status Badge */}
        <div className="mt-3 flex items-baseline justify-between gap-2">
          <span className="text-3xl font-bold tracking-tight text-white">
            {value}
          </span>
          {statusLabel && (
            <span
              className={`text-xs font-medium px-2.5 py-0.5 rounded-full border ${styles.badge}`}
            >
              {statusLabel}
            </span>
          )}
        </div>
      </div>
      {/* Bottom Row: Subtitle & Sample Size (n) */}
      <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
        <span>{subtitle}</span>
        {sampleInfo && (
          <span className="font-mono text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
            {sampleInfo}
          </span>
        )}
      </div>
    </div>
  );
}