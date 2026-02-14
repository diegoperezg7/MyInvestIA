"use client";

import { useState, useEffect, useCallback } from "react";
import { Bot, Play, Square, RefreshCw, History, AlertTriangle } from "lucide-react";
import { fetchAPI, postAPI } from "@/lib/api";
import type { AgentStatus, AlertHistoryEntry } from "@/types";

export default function AgentStatusPanel() {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [history, setHistory] = useState<AlertHistoryEntry[]>([]);
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState<"status" | "history">("status");
  const [error, setError] = useState("");

  const loadStatus = useCallback(async () => {
    try {
      const data = await fetchAPI<AgentStatus>("/api/v1/agents/status");
      setStatus(data);
    } catch {
      /* ignore */
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const data = await fetchAPI<{ alerts: AlertHistoryEntry[] }>(
        "/api/v1/agents/alerts/history?limit=30",
        { skipCache: true }
      );
      setHistory(data.alerts || []);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadStatus();
    loadHistory();
    const iv = setInterval(loadStatus, 60_000);
    return () => clearInterval(iv);
  }, [loadStatus, loadHistory]);

  const runAgents = async () => {
    setRunning(true);
    setError("");
    try {
      await postAPI("/api/v1/agents/run", {});
      await loadStatus();
      await loadHistory();
    } catch (e) {
      setError("Failed to run agents");
    } finally {
      setRunning(false);
    }
  };

  const toggleScheduler = async () => {
    try {
      if (status?.running) {
        await postAPI("/api/v1/agents/scheduler/stop", {});
      } else {
        await postAPI("/api/v1/agents/scheduler/start?interval=30", {});
      }
      await loadStatus();
    } catch {
      setError("Scheduler toggle failed");
    }
  };

  const severityColor: Record<string, string> = {
    critical: "text-red-400 bg-red-400/10",
    high: "text-orange-400 bg-orange-400/10",
    medium: "text-yellow-400 bg-yellow-400/10",
    low: "text-blue-400 bg-blue-400/10",
  };

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-oracle-accent" />
          <h3 className="font-semibold text-oracle-text text-sm">AI Agents</h3>
          {status?.running && (
            <span className="text-[10px] px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded">
              ACTIVE
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={runAgents}
            disabled={running}
            className="p-1.5 rounded hover:bg-oracle-border transition-colors disabled:opacity-50"
            title="Run agents now"
          >
            <Play className={`w-3.5 h-3.5 ${running ? "animate-pulse text-green-400" : "text-oracle-muted"}`} />
          </button>
          <button
            onClick={toggleScheduler}
            className="p-1.5 rounded hover:bg-oracle-border transition-colors"
            title={status?.running ? "Stop scheduler" : "Start scheduler"}
          >
            {status?.running ? (
              <Square className="w-3.5 h-3.5 text-red-400" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5 text-oracle-muted" />
            )}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-3 border-b border-oracle-border">
        <button
          onClick={() => setTab("status")}
          className={`text-xs pb-2 px-1 border-b-2 transition-colors ${
            tab === "status"
              ? "border-oracle-accent text-oracle-accent"
              : "border-transparent text-oracle-muted hover:text-oracle-text"
          }`}
        >
          Status
        </button>
        <button
          onClick={() => {
            setTab("history");
            loadHistory();
          }}
          className={`text-xs pb-2 px-1 border-b-2 transition-colors flex items-center gap-1 ${
            tab === "history"
              ? "border-oracle-accent text-oracle-accent"
              : "border-transparent text-oracle-muted hover:text-oracle-text"
          }`}
        >
          <History className="w-3 h-3" /> History
        </button>
      </div>

      {error && <p className="text-red-400 text-xs mb-2">{error}</p>}

      {tab === "status" && status && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-oracle-bg rounded p-2">
              <span className="text-oracle-muted">Agents</span>
              <p className="text-oracle-text font-mono">{status.agents.length}</p>
            </div>
            <div className="bg-oracle-bg rounded p-2">
              <span className="text-oracle-muted">Last alerts</span>
              <p className="text-oracle-text font-mono">{status.last_alert_count}</p>
            </div>
          </div>
          {status.last_run && (
            <p className="text-[10px] text-oracle-muted">
              Last run: {new Date(status.last_run).toLocaleString()}
            </p>
          )}
          <div className="flex flex-wrap gap-1 mt-2">
            {status.agents.map((name) => (
              <span
                key={name}
                className="text-[10px] px-1.5 py-0.5 bg-oracle-border rounded text-oracle-muted"
              >
                {name}
              </span>
            ))}
          </div>
        </div>
      )}

      {tab === "history" && (
        <div className="space-y-1.5 max-h-64 overflow-y-auto">
          {history.length === 0 ? (
            <p className="text-oracle-muted text-xs text-center py-4">No alert history yet</p>
          ) : (
            history.map((alert) => (
              <div
                key={alert.id}
                className="bg-oracle-bg rounded p-2 flex items-start gap-2"
              >
                <AlertTriangle className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${
                  alert.severity === "high" || alert.severity === "critical"
                    ? "text-orange-400"
                    : "text-yellow-400"
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className={`text-[10px] px-1 py-0.5 rounded ${severityColor[alert.severity] || ""}`}>
                      {alert.severity}
                    </span>
                    {alert.symbol && (
                      <span className="text-[10px] text-oracle-accent font-mono">{alert.symbol}</span>
                    )}
                  </div>
                  <p className="text-xs text-oracle-text mt-0.5 truncate">{alert.title}</p>
                  {alert.created_at && (
                    <p className="text-[10px] text-oracle-muted mt-0.5">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
