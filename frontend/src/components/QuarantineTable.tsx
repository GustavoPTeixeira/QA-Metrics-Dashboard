"use client";

import { useState } from "react";
import { Check, ShieldAlert, ShieldBan } from "lucide-react";
import { QuarantineCandidate } from "@/types/api";

interface QuarantineTableProps {
  candidates: QuarantineCandidate[];
}

export function QuarantineTable({ candidates }: QuarantineTableProps) {
  const [quarantinedIds, setQuarantinedIds] = useState<Record<string, boolean>>(
    {}
  );

  const toggleQuarantine = (scenarioId: string) => {
    setQuarantinedIds((prev) => ({
      ...prev,
      [scenarioId]: !prev[scenarioId],
    }));
  };

  return (
    <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-6 shadow-sm flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">
                Flakiness &ldquo;Hall of Shame&rdquo; (Quarantine)
              </h2>
              <p className="text-xs text-slate-400">
                Scenarios exceeding ≥10% flakiness threshold over ≥10 runs
              </p>
            </div>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
            {candidates.length} {candidates.length === 1 ? "Candidate" : "Candidates"}
          </span>
        </div>

        {/* Table or Empty State */}
        {candidates.length === 0 ? (
          <div className="py-12 text-center border border-dashed border-slate-800 rounded-lg">
            <p className="text-sm text-slate-400">
              No unstable scenarios meet quarantine criteria in this window.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase text-slate-400">
                  <th className="py-3 pr-4 font-semibold">Scenario</th>
                  <th className="py-3 px-3 font-semibold">Module / Squad</th>
                  <th className="py-3 px-3 text-center font-semibold">
                    Flaky / Total
                  </th>
                  <th className="py-3 px-3 text-center font-semibold">
                    Flakiness %
                  </th>
                  <th className="py-3 pl-4 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {candidates.map((item) => {
                  const isQuarantined = !!quarantinedIds[item.scenario_id];

                  return (
                    <tr
                      key={item.scenario_id}
                      className="hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="py-3.5 pr-4">
                        <div className="font-mono text-xs font-medium text-white">
                          {item.scenario_title}
                        </div>
                        <div className="font-mono text-[11px] text-slate-500 mt-0.5">
                          ID: {item.scenario_id.slice(0, 12)}...
                        </div>
                      </td>
                      <td className="py-3.5 px-3">
                        <div className="text-xs font-medium text-slate-200">
                          {item.module_name}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {item.owner_team}
                        </div>
                      </td>
                      <td className="py-3.5 px-3 text-center font-mono text-xs text-slate-300">
                        {item.flaky_runs} / {item.total_runs}
                      </td>
                      <td className="py-3.5 px-3 text-center">
                        <span className="inline-block font-mono text-xs font-bold px-2.5 py-1 rounded-md bg-rose-500/15 text-rose-300 border border-rose-500/30">
                          {item.flakiness_pct}%
                        </span>
                      </td>
                      <td className="py-3.5 pl-4 text-right">
                        <button
                          onClick={() => toggleQuarantine(item.scenario_id)}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                            isQuarantined
                              ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                              : "bg-slate-800 hover:bg-rose-500/20 text-slate-200 hover:text-rose-200 border-slate-700 hover:border-rose-500/40"
                          }`}
                        >
                          {isQuarantined ? (
                            <>
                              <Check className="w-3.5 h-3.5" />
                              Quarantined
                            </>
                          ) : (
                            <>
                              <ShieldBan className="w-3.5 h-3.5" />
                              Isolate in CI
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}