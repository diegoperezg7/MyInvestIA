"use client";

import { useCallback, useEffect, useState } from "react";
import { Bell, Link2, RefreshCw, Send } from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI, postAPI } from "@/lib/api";
import type {
  PersonalBotActionResponse,
  PersonalBotRunResponse,
  PersonalBotStatus,
} from "@/types";

const EMPTY_STATUS: PersonalBotStatus = {
  available: false,
  enabled: false,
  connected: false,
  status: "disconnected",
  bot_name: null,
  bot_username: null,
  chat_id: null,
  chat_name: null,
  telegram_username: null,
  cadence_minutes: 30,
  min_severity: "high",
  include_briefing: true,
  include_inbox: true,
  include_portfolio: true,
  include_watchlist: true,
  include_macro: true,
  include_news: true,
  include_theses: true,
  include_buy_sell: true,
  send_only_on_changes: true,
  provisioned_defaults: false,
  pending_code: null,
  pending_expires_at: null,
  connect_url: null,
  verified_at: null,
  last_run_at: null,
  last_delivery_at: null,
  last_test_at: null,
  last_error: null,
  last_reason: null,
  last_message_count: 0,
  last_alert_count: 0,
  history: [],
};

export default function NotificationsPanel() {
  const { user, loading: authLoading } = useAuth();
  const [status, setStatus] = useState<PersonalBotStatus>(EMPTY_STATUS);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const load = useCallback(async () => {
    if (!user) {
      setStatus(EMPTY_STATUS);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetchAPI<PersonalBotStatus>("/api/v1/notifications/bot/status", {
        skipCache: true,
      });
      setStatus({ ...EMPTY_STATUS, ...res });
    } catch {
      // Keep the last known status instead of downgrading to "disconnected"
      // on a transient auth or network race.
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (authLoading) return;
    void load();
  }, [authLoading, load]);

  async function handleTest() {
    setSending(true);
    setFeedback(null);
    try {
      const res = await postAPI<PersonalBotActionResponse>(
        "/api/v1/notifications/bot/test",
        {},
      );
      setStatus({ ...EMPTY_STATUS, ...res.status });
      setFeedback({
        type: res.success ? "success" : "error",
        text: res.message,
      });
    } catch (error) {
      setFeedback({
        type: "error",
        text: error instanceof Error ? error.message : "No se pudo enviar el test",
      });
    } finally {
      setSending(false);
    }
  }

  async function handleRunNow() {
    setSending(true);
    setFeedback(null);
    try {
      const res = await postAPI<PersonalBotRunResponse>(
        "/api/v1/notifications/bot/run",
        {},
      );
      setStatus({ ...EMPTY_STATUS, ...res.status });
      setFeedback({
        type: res.success || res.skipped ? "success" : "error",
        text: res.message,
      });
    } catch (error) {
      setFeedback({
        type: "error",
        text: error instanceof Error ? error.message : "No se pudo ejecutar el bot",
      });
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="rounded-2xl border border-oracle-border bg-oracle-panel p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium uppercase tracking-wide text-oracle-muted">
            Bot personal
          </h3>
          <p className="mt-1 text-xs text-oracle-muted">
            Alertas, inbox y tesis en Telegram.
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={sending}
          className="inline-flex items-center gap-1 rounded-lg border border-oracle-border px-2.5 py-1.5 text-xs text-oracle-text transition-colors hover:border-oracle-accent disabled:opacity-50"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Actualizar
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-oracle-muted">Comprobando estado del bot...</p>
      ) : !status.available ? (
        <p className="text-sm text-oracle-muted">
          El bot compartido de Telegram aun no esta habilitado en el servidor.
        </p>
      ) : (
        <div className="space-y-3">
          <div className="rounded-xl border border-oracle-border bg-oracle-bg/40 p-3">
            <div className="flex items-center gap-2">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  status.connected ? "bg-oracle-green" : status.status === "pending" ? "bg-oracle-yellow" : "bg-oracle-red"
                }`}
              />
              <span className="text-sm text-oracle-text">
                {status.connected
                  ? `Conectado${status.chat_name ? ` · ${status.chat_name}` : ""}`
                  : status.status === "pending"
                    ? "Pendiente de verificar"
                    : "No conectado"}
              </span>
            </div>
            <p className="mt-2 text-xs text-oracle-muted">
              Cadencia {status.cadence_minutes}m · umbral {status.min_severity} · {status.last_message_count} mensajes en el ultimo envio
            </p>
          </div>

          {status.connected ? (
            <div className="grid gap-2 sm:grid-cols-2">
              <button
                onClick={handleTest}
                disabled={sending}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-oracle-accent/30 bg-oracle-accent/10 px-3 py-2 text-sm text-oracle-accent transition-colors hover:bg-oracle-accent/20 disabled:opacity-50"
              >
                <Bell className="h-4 w-4" />
                Enviar test
              </button>
              <button
                onClick={handleRunNow}
                disabled={sending}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-oracle-green/30 bg-oracle-green/10 px-3 py-2 text-sm text-oracle-green transition-colors hover:bg-oracle-green/20 disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
                Ejecutar ahora
              </button>
            </div>
          ) : (
            <div className="rounded-xl border border-oracle-border bg-oracle-bg/40 p-3 text-sm text-oracle-muted">
              <p>Conectalo desde Ajustes para recibir avisos en tu bot personal de cartera, noticias y señales buy/sell.</p>
              {status.connect_url && (
                <a
                  href={status.connect_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-2 font-medium text-oracle-accent hover:underline"
                >
                  Abrir Telegram
                  <Link2 className="h-4 w-4" />
                </a>
              )}
            </div>
          )}

          {feedback && (
            <p
              className={`text-xs ${
                feedback.type === "success" ? "text-oracle-green" : "text-oracle-red"
              }`}
            >
              {feedback.text}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
