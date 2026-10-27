import { Grid } from "lucide-react";
import { HeatmapResponse } from "@/types/api";

interface RiskHeatmapProps {
  heatmap: HeatmapResponse;
}

function getCellColor(severity: string, count: number): string {
  if (count === 0) {
    return "bg-slate-950/60 text-slate-600 border-slate-800/60";
  }

  if (severity === "Critical") {
    return count >= 3
      ? "bg-rose-500/30 text-rose-200 border-rose-500/50 font-bold"
      : "bg-rose-500/15 text-rose-300 border-rose-500/30 font-semibold";
  }

  if (severity === "High") {
    return count >= 4
      ? "bg-amber-500/30 text-amber-200 border-amber-500/50 font-bold"
      : "bg-amber-500/15 text-amber-300 border-amber-500/30 font-semibold";
  }

  if (severity === "Medium") {
    return "bg-indigo-500/15 text-indigo-300 border-indigo-500/30";
  }

  return "bg-slate-800/80 text-slate-300 border-slate-700";
}

export function RiskHeatmap({ heatmap }: RiskHeatmapProps) {
  const { modules, severities, matrix } = heatmap;

  return (
    <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
            <Grid className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">
              Defect Risk Heatmap (Module × Severity)
            </h2>
            <p className="text-xs text-slate-400">
              Concentration of defects across product architecture
            </p>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800 text-xs uppercase text-slate-400">
              <th className="py-3 pr-4 font-semibold">Module</th>
              {severities.map((sev) => (
                <th key={sev} className="py-3 px-3 text-center font-semibold">
                  {sev}
                </th>
              ))}
              <th className="py-3 pl-4 text-right font-semibold">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {modules.map((mod) => {
              const row = matrix[mod] || {};
              const rowTotal = severities.reduce(
                (acc, sev) => acc + (row[sev] || 0),
                0
              );

              return (
                <tr
                  key={mod}
                  className="hover:bg-slate-800/30 transition-colors"
                >
                  <td className="py-3 pr-4 font-medium text-slate-200">
                    {mod}
                  </td>
                  {severities.map((sev) => {
                    const count = row[sev] || 0;
                    return (
                      <td key={sev} className="py-2 px-2 text-center">
                        <div
                          className={`py-2 px-3 rounded-lg border text-xs font-mono transition-all ${getCellColor(
                            sev,
                            count
                          )}`}
                        >
                          {count}
                        </div>
                      </td>
                    );
                  })}
                  <td className="py-3 pl-4 text-right font-mono font-semibold text-slate-300">
                    {rowTotal}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}