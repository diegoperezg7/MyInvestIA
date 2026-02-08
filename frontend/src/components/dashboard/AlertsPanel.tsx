"use client";

import { useState } from "react";
import { fetchAPI } from "@/lib/api";
import type { AlertList, Alert } from "@/types";

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-oracle-red/20 border-oracle-red/50 text-oracle-red",
  high: "bg-oracle-red/10 border-oracle-red/30 text-oracle-red",
  medium: "bg-oracle-yellow/10 border-oracle-yellow/30 text-oracle-yellow",
  low: "bg-oracle-accent/10 border-oracle-accent/30 text-oracle-accent",
};

const ACTION_STYLES: Record<string, string> = {
  buy: "text-oracle-green",
  sell: "text-oracle-red",
  wait: "text-oracle-yellow",
  monitor: "text-oracle-accent",
};

function AlertCard({ alert }: { alert: Alert }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`border rounded-lg px-4 py-3 cursor-pointer transition-colors ${
        SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.low
      }`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium uppercase">
            {alert.severity}
          </span>
          <span className="text-sm font-medium text-white">{alert.title}</span>
        </div>
        <span
          className={`text-xs font-medium uppercase ${
            ACTION_STYLES[alert.suggested_action] || ""
          }`}
        >
          {alert.suggested_action}
        </span>
      </div>

      {expanded && (
        <div className="mt-2 space-y-1 text-sm">
          <p className="text-oracle-text">{alert.description}</p>
          <p className="text-oracle-muted text-xs">{alert.reasoning}</p>
          <div className="flex items-center gap-3 text-xs text-oracle-muted mt-1">
            <span>Confidence: {(alert.confidence * 100).toFixed(0)}%</span>
            <span>Type: {alert.type}</span>
            {alert.asset_symbol && <span>Asset: {alert.asset_symbol}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanned, setScanned] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleScan = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAPI<AlertList>("/api/v1/alerts/?scan=true");
      setAlerts(data.alerts);
      setScanned(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          Active Alerts
        </h3>
        <button
          onClick={handleScan}
          disabled={loading}
          className="bg-oracle-accent text-white text-xs px-3 py-1.5 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
        >
          {loading ? "Scanning..." : "Scan Now"}
        </button>
      </div>

      {error && <p className="text-oracle-red text-sm mb-2">{error}</p>}

      {!scanned && alerts.length === 0 && (
        <p className="text-oracle-muted text-sm">
          Click &quot;Scan Now&quot; to analyze your portfolio and watchlist
          assets for alerts.
        </p>
      )}

      {scanned && alerts.length === 0 && (
        <p className="text-oracle-muted text-sm">
          No alerts found. Your assets are within normal parameters.
        </p>
      )}

      {alerts.length > 0 && (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
