"use client";

import { useState } from "react";
import { CloudDownload, Kanban, Loader2 } from "lucide-react";
import { BoardTicket } from "@/types/api";
import { syncExternalBoard } from "@/lib/api";

interface BoardExplorerProps {
  tickets: BoardTicket[];
  onSyncComplete: () => void;
}

const PROVIDER_BADGE: Record<string, string> = {
  Jira: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  GitHub: "bg-slate-700/60 text-slate-200 border-slate-600",
  "Azure DevOps": "bg-sky-500/15 text-sky-300 border-sky-500/30",
};

const SEVERITY_BADGE: Record<string, string> = {
  Critical: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  High: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  Medium: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
  Low: "bg-slate-800 text-slate-300 border-slate-700",
};

const STATUS_BADGE: Record<string, string> = {
  Open: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  "In Progress": "bg-amber-500/10 text-amber-400 border-amber-500/20",
  Resolved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Closed: "bg-slate-800 text-slate-400 border-slate-700",
};

export function BoardExplorer({ tickets, onSyncComplete }: BoardExplorerProps) {
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [provider, setProvider] = useState<"jira" | "github" | "azure-devops">("jira");
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const [jiraUrl, setJiraUrl] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraToken, setJiraToken] = useState("");
  const [jiraProject, setJiraProject] = useState("");

  const [githubRepo, setGithubRepo] = useState("");
  const [githubToken, setGithubToken] = useState("");

  const [adoOrgUrl, setAdoOrgUrl] = useState("");
  const [adoProject, setAdoProject] = useState("");
  const [adoPat, setAdoPat] = useState("");

  const handleSync = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSyncing(true);
    setSyncMessage(null);
    setSyncError(null);

    try {
      let payload: Record<string, unknown> = {};
      if (provider === "jira") {
        payload = {
          base_url: jiraUrl,
          email: jiraEmail,
          api_token: jiraToken,
          project_key: jiraProject,
        };
      } else if (provider === "github") {
        payload = {
          repo_full_name: githubRepo,
          token: githubToken || null,
        };
      } else {
        payload = {
          org_url: adoOrgUrl,
          project: adoProject,
          pat: adoPat,
        };
      }

      const res = await syncExternalBoard(provider, payload);
      setSyncMessage(
        `Synced ${res.synced_total} tickets (${res.created} new, ${res.updated} updated).`
      );
      onSyncComplete();
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Board sync failed.");
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="rounded-xl bg-slate-900/90 border border-slate-800 p-6 shadow-sm space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
            <Kanban className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">
              Live Defect Board &amp; External Integrations
            </h2>
            <p className="text-xs text-slate-400">
              Unified stream of Jira, GitHub Issues, and Azure DevOps work items
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowSyncModal(!showSyncModal)}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition-colors self-start sm:self-auto"
        >
          <CloudDownload className="w-4 h-4" />
          {showSyncModal ? "Hide Board Connector" : "Connect Jira / GitHub / ADO"}
        </button>
      </div>

      {showSyncModal && (
        <form
          onSubmit={handleSync}
          className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-4"
        >
          <div className="flex items-center gap-2">
            {(["jira", "github", "azure-devops"] as const).map((p) => (
              <button
                type="button"
                key={p}
                onClick={() => setProvider(p)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  provider === p
                    ? "bg-indigo-600/20 text-indigo-300 border-indigo-500/40"
                    : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200"
                }`}
              >
                {p === "jira"
                  ? "Jira Cloud"
                  : p === "github"
                  ? "GitHub Issues"
                  : "Azure DevOps Boards"}
              </button>
            ))}
          </div>

          {provider === "jira" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <input
                required
                placeholder="Jira URL (https://your-org.atlassian.net)"
                value={jiraUrl}
                onChange={(e) => setJiraUrl(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white"
              />
              <input
                required
                type="email"
                placeholder="Atlassian Email"
                value={jiraEmail}
                onChange={(e) => setJiraEmail(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white"
              />
              <input
                required
                type="password"
                placeholder="Atlassian API Token"
                value={jiraToken}
                onChange={(e) => setJiraToken(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white"
              />
              <input
                required
                placeholder="Project Key (e.g. QA or KAN)"
                value={jiraProject}
                onChange={(e) => setJiraProject(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white"
              />
            </div>
          )}

          {provider === "github" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input
                required
                placeholder="owner/repository (e.g. fastapi/fastapi)"
                value={githubRepo}
                onChange={(e) => setGithubRepo(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white"
              />
              <input
                type="password"
                placeholder="GitHub Personal Access Token (optional for public repos)"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white"
              />
            </div>
          )}

          {provider === "azure-devops" && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <input
                required
                placeholder="Org URL (https://dev.azure.com/your-org)"
                value={adoOrgUrl}
                onChange={(e) => setAdoOrgUrl(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white"
              />
              <input
                required
                placeholder="Project Name"
                value={adoProject}
                onChange={(e) => setAdoProject(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white"
              />
              <input
                required
                type="password"
                placeholder="Personal Access Token (PAT)"
                value={adoPat}
                onChange={(e) => setAdoPat(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white"
              />
            </div>
          )}

          <div className="flex items-center justify-between gap-4">
            <div className="text-xs">
              {syncMessage && (
                <span className="text-emerald-400 font-medium">{syncMessage}</span>
              )}
              {syncError && (
                <span className="text-rose-400 font-medium">{syncError}</span>
              )}
            </div>
            <button
              type="submit"
              disabled={isSyncing}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-50"
            >
              {isSyncing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {isSyncing ? "Syncing Board..." : "Sync Tickets Now"}
            </button>
          </div>
        </form>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800 text-xs uppercase text-slate-400">
              <th className="py-3 pr-4 font-semibold">Source</th>
              <th className="py-3 px-3 font-semibold">Key</th>
              <th className="py-3 px-3 font-semibold">Title</th>
              <th className="py-3 px-3 font-semibold">Module</th>
              <th className="py-3 px-3 text-center font-semibold">Severity</th>
              <th className="py-3 px-3 text-center font-semibold">Status</th>
              <th className="py-3 pl-4 text-right font-semibold">Environment</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {tickets.map((t) => (
              <tr key={t.id} className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 pr-4">
                  <span
                    className={`inline-block text-[11px] font-medium px-2 py-0.5 rounded border ${
                      PROVIDER_BADGE[t.provider] || PROVIDER_BADGE.Jira
                    }`}
                  >
                    {t.provider}
                  </span>
                </td>
                <td className="py-3 px-3 font-mono text-xs font-semibold text-white">
                  {t.external_key}
                </td>
                <td className="py-3 px-3 text-xs text-slate-200 max-w-md truncate">
                  {t.title}
                </td>
                <td className="py-3 px-3 text-xs text-slate-300">
                  {t.module_name}
                </td>
                <td className="py-3 px-3 text-center">
                  <span
                    className={`inline-block text-[11px] font-medium px-2 py-0.5 rounded border ${
                      SEVERITY_BADGE[t.severity] || SEVERITY_BADGE.Medium
                    }`}
                  >
                    {t.severity}
                  </span>
                </td>
                <td className="py-3 px-3 text-center">
                  <span
                    className={`inline-block text-[11px] font-medium px-2 py-0.5 rounded-full border ${
                      STATUS_BADGE[t.status] || STATUS_BADGE.Open
                    }`}
                  >
                    {t.status}
                  </span>
                </td>
                <td className="py-3 pl-4 text-right font-mono text-xs text-slate-400">
                  {t.found_in}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}