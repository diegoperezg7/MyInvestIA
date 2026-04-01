"use client";

import { useState } from "react";
import { fetchAPI, postAPI } from "@/lib/api";
import Sparkline from "@/components/ui/Sparkline";
import useSparklines from "@/hooks/useSparklines";
import type { AlertList, Alert, ScanAndNotifyResponse } from "@/types";

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

function AlertCard({ alert, sparkData }: { alert: Alert; sparkData: number[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <button
      type="button"
      className={`border rounded-lg px-4 py-3 cursor-pointer transition-colors ${
        SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.low
      } w-full text-left`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium uppercase">
            {alert.severity}
          </span>
          <span className="text-sm font-medium text-oracle-text">{alert.title}</span>
        </div>
        <div className="flex items-center gap-2">
          {alert.asset_symbol && (
            <Sparkline data={sparkData} width={48} height={18} />
          )}
          <span
            className={`text-xs font-medium uppercase ${
              ACTION_STYLES[alert.suggested_action] || ""
            }`}
          >
            {alert.suggested_action}
          </span>
        </div>
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
    </button>
  );
}

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [notifying, setNotifying] = useState(false);
  const [scanned, setScanned] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notifyResult, setNotifyResult] = useState<string | null>(null);

  const alertSymbols = alerts
    .map((a) => a.asset_symbol)
    .filter((s): s is string => !!s);
  const sparklines = useSparklines(alertSymbols);

  const handleScan = async () => {
    setLoading(true);
    setError(null);
    setNotifyResult(null);
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

  const handleScanAndNotify = async () => {
    setNotifying(true);
    setError(null);
    setNotifyResult(null);
    try {
      const data = await postAPI<ScanAndNotifyResponse>(
        "/api/v1/alerts/scan-and-notify?min_severity=high",
        {}
      );
      setAlerts(data.alerts);
      setScanned(true);
      if (!data.telegram_configured) {
        setNotifyResult("No tienes conectado tu bot personal de Telegram para enviar alertas.");
      } else if (data.total_notified > 0) {
        setNotifyResult(
          `Enviada${data.total_notified > 1 ? "s" : ""} ${data.total_notified} alerta${data.total_notified > 1 ? "s" : ""} a Telegram`
        );
      } else {
        setNotifyResult(
          `${data.total_alerts} alerta${data.total_alerts !== 1 ? "s" : ""} detectada${data.total_alerts !== 1 ? "s" : ""}, pero ninguna superó el umbral de envío`
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fallo al escanear y notificar");
    } finally {
      setNotifying(false);
    }
  };

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          Alertas activas
        </h3>
        <div className="flex gap-2">
          <button
            onClick={handleScanAndNotify}
            disabled={loading || notifying}
            className="bg-oracle-green/20 text-oracle-green text-xs px-3 py-1.5 rounded border border-oracle-green/30 hover:bg-oracle-green/30 disabled:opacity-50 transition-colors"
          >
            {notifying ? "Enviando..." : "Escanear y avisar"}
          </button>
          <button
            onClick={handleScan}
            disabled={loading || notifying}
            className="bg-oracle-accent text-white text-xs px-3 py-1.5 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
          >
            {loading ? "Escaneando..." : "Escanear"}
          </button>
        </div>
      </div>

      {error && <p className="text-oracle-red text-sm mb-2">{error}</p>}
      {notifyResult && (
        <p className="text-oracle-accent text-xs mb-2">{notifyResult}</p>
      )}

      {!scanned && alerts.length === 0 && (
        <p className="text-oracle-muted text-sm">
          Pulsa &quot;Escanear&quot; para analizar activos, o &quot;Escanear y avisar&quot; para enviar las alertas más relevantes a tu Telegram.
        </p>
      )}

      {scanned && alerts.length === 0 && (
        <p className="text-oracle-muted text-sm">
          No se han detectado alertas. Tus activos están dentro de parámetros normales.
        </p>
      )}

      {alerts.length > 0 && (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {alerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              sparkData={alert.asset_symbol ? (sparklines[alert.asset_symbol] ?? []) : []}
            />
          ))}
        </div>
      )}
    </div>
  );
}
