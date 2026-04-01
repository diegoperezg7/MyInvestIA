"use client";

import { useEffect, useState, type ReactNode } from "react";
import {
  Bell,
  Bot,
  Globe,
  Link2,
  RefreshCw,
  Save,
  Send,
  Target,
  User,
} from "lucide-react";

import { fetchAPI, patchAPI, postAPI } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { useAuth } from "@/contexts/AuthContext";
import type {
  PersonalBotActionResponse,
  PersonalBotProvisionResponse,
  PersonalBotRunResponse,
  PersonalBotStatus,
  UserProfile,
} from "@/types";

const DEFAULT_PROFILE: UserProfile = {
  display_name: "",
  risk_tolerance: "moderate",
  investment_horizon: "medium",
  goals: [],
  preferred_currency: "EUR",
  notification_frequency: "important",
  notification_channels: ["telegram"],
  language: "es",
  theme: "dark",
  assistant_mode: "balanced",
  default_horizon: "medium",
  inbox_scope_preference: "portfolio",
};

const RISK_OPTIONS = [
  { value: "conservative", label: "Conservador", desc: "Prioriza protección y drawdown bajo" },
  { value: "moderate", label: "Moderado", desc: "Equilibrio entre riesgo y oportunidad" },
  { value: "aggressive", label: "Agresivo", desc: "Más tolerancia a volatilidad y momentum" },
] as const;

const HORIZON_OPTIONS = [
  { value: "short", label: "Corto plazo", desc: "< 1 año" },
  { value: "medium", label: "Medio plazo", desc: "1-5 años" },
  { value: "long", label: "Largo plazo", desc: "5+ años" },
] as const;

const ASSISTANT_MODES = [
  { value: "prudent", label: "Prudent", desc: "Reduce ideas exploratorias y prioriza confirmación" },
  { value: "balanced", label: "Balanced", desc: "Mezcla riesgo, oportunidades y catalizadores" },
  { value: "proactive", label: "Proactive", desc: "Empuja más ideas tempranas y research" },
] as const;

const INBOX_SCOPE_OPTIONS = [
  { value: "portfolio", label: "Portfolio primero" },
  { value: "watchlist", label: "Watchlist primero" },
  { value: "macro", label: "Macro primero" },
  { value: "research", label: "Research primero" },
] as const;

const NOTIFICATION_OPTIONS = [
  { value: "all", label: "Todas" },
  { value: "important", label: "Importantes" },
  { value: "critical_only", label: "Solo críticas" },
  { value: "none", label: "Ninguna" },
] as const;

const GOAL_PRESETS = [
  "Jubilación",
  "Libertad financiera",
  "Ahorro para vivienda",
  "Ingresos pasivos",
  "Crecimiento de capital",
  "Diversificación",
];

const EMPTY_BOT_STATUS: PersonalBotStatus = {
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

const BOT_CADENCE_OPTIONS = [15, 30, 60, 180, 360] as const;
const BOT_SEVERITY_OPTIONS = [
  { value: "all", label: "Todo" },
  { value: "medium", label: "Medium+" },
  { value: "high", label: "High+" },
  { value: "critical", label: "Critical" },
] as const;
const BOT_SIGNAL_OPTIONS = [
  { key: "include_briefing", label: "Briefing", desc: "Resumen corto del dia" },
  { key: "include_inbox", label: "Inbox", desc: "Top prioridades y why now" },
  { key: "include_portfolio", label: "Cartera", desc: "Escaneo de tus posiciones" },
  { key: "include_watchlist", label: "Watchlist", desc: "Ideas y riesgos fuera de cartera" },
  { key: "include_macro", label: "Macro", desc: "Catalizadores, calendario y contexto" },
  { key: "include_news", label: "Noticias", desc: "Cobertura de eventos y titulares" },
  { key: "include_theses", label: "Tesis", desc: "Avisos cuando una tesis se tensiona" },
  { key: "include_buy_sell", label: "Buy / Sell", desc: "Señales accionables del scanner" },
  { key: "send_only_on_changes", label: "Solo cambios", desc: "Evita resumentes repetidos" },
] as const;

type BotToggleKey = (typeof BOT_SIGNAL_OPTIONS)[number]["key"];

function Card({
  title,
  icon,
  children,
  className = "",
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-2xl border border-oracle-border bg-oracle-panel p-4 ${className}`}>
      <div className="mb-4 flex items-center gap-2">
        {icon}
        <h3 className="text-sm font-medium text-oracle-text">{title}</h3>
      </div>
      {children}
    </section>
  );
}

export default function SettingsView() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile>(DEFAULT_PROFILE);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [botStatus, setBotStatus] = useState<PersonalBotStatus>(EMPTY_BOT_STATUS);
  const [botLoading, setBotLoading] = useState(true);
  const [botBusy, setBotBusy] = useState<string | null>(null);
  const [botFeedback, setBotFeedback] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [profileResult, botResult] = await Promise.all([
          fetchAPI<UserProfile>("/api/v1/user/profile", { skipCache: true }),
          fetchAPI<PersonalBotStatus>("/api/v1/notifications/bot/status", { skipCache: true }),
        ]);
        setProfile({ ...DEFAULT_PROFILE, ...profileResult });
        setBotStatus({ ...EMPTY_BOT_STATUS, ...botResult });
      } catch {
        setBotStatus(EMPTY_BOT_STATUS);
      } finally {
        setBotLoading(false);
      }
    };
    load();
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const token = getToken();
      const response = await fetch("/api/v1/user/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify(profile),
      });
      if (response.ok) {
        setSaved(true);
        window.setTimeout(() => setSaved(false), 2000);
      }
    } finally {
      setSaving(false);
    }
  };

  const toggleGoal = (goal: string) => {
    setProfile((current) => ({
      ...current,
      goals: current.goals.includes(goal)
        ? current.goals.filter((item) => item !== goal)
        : [...current.goals, goal],
    }));
  };

  const loadBotStatus = async () => {
    const status = await fetchAPI<PersonalBotStatus>("/api/v1/notifications/bot/status", {
      skipCache: true,
    });
    setBotStatus({ ...EMPTY_BOT_STATUS, ...status });
  };

  const setBotResult = (
    type: "success" | "error",
    text: string,
    status?: PersonalBotStatus,
  ) => {
    if (status) {
      setBotStatus({ ...EMPTY_BOT_STATUS, ...status });
    }
    setBotFeedback({ type, text });
  };

  const runBotAction = async (key: string, action: () => Promise<void>) => {
    setBotBusy(key);
    setBotFeedback(null);
    try {
      await action();
    } catch (error) {
      setBotResult(
        "error",
        error instanceof Error ? error.message : "Bot action failed",
      );
    } finally {
      setBotBusy(null);
    }
  };

  const updateBotConfig = (patch: Partial<PersonalBotStatus>) =>
    runBotAction("config", async () => {
      const status = await patchAPI<PersonalBotStatus>("/api/v1/notifications/bot/config", patch);
      setBotResult("success", "Configuracion del bot actualizada", status);
    });

  const toggleBotOption = (key: BotToggleKey) => {
    void updateBotConfig({ [key]: !botStatus[key] } as Partial<PersonalBotStatus>);
  };

  const formatTimestamp = (value: string | null) => {
    if (!value) return "Nunca";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  };

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <section className="oracle-hero-surface rounded-2xl border border-oracle-border p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <span className="rounded-full border border-oracle-accent/30 bg-oracle-accent/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-oracle-accent">
              Settings
            </span>
            <h2 className="mt-3 text-2xl font-semibold text-oracle-text">Perfil operativo de la app</h2>
            <p className="mt-1 max-w-3xl text-sm text-oracle-muted">
              Estas preferencias alimentan el ranking del Inbox, el tono del asistente y la priorización por horizonte/riesgo.
            </p>
          </div>
          <button
            onClick={save}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl border border-oracle-accent/30 bg-oracle-accent/15 px-4 py-3 text-sm font-medium text-oracle-accent transition-colors hover:bg-oracle-accent/25 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saved ? "Guardado" : saving ? "Guardando..." : "Guardar"}
          </button>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Cuenta" icon={<User className="h-4 w-4 text-oracle-accent" />}>
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-xs text-oracle-muted">Email</p>
              <div className="mt-1 rounded-xl border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-oracle-text">
                {user?.email}
              </div>
            </div>
            <div>
              <p className="text-xs text-oracle-muted">Nombre visible</p>
              <input
                type="text"
                value={profile.display_name}
                onChange={(event) => setProfile({ ...profile, display_name: event.target.value })}
                className="mt-1 w-full rounded-xl border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-oracle-text placeholder:text-oracle-muted"
                placeholder="Tu nombre"
              />
            </div>
          </div>
        </Card>

        <Card title="Asistente" icon={<Bot className="h-4 w-4 text-oracle-accent" />}>
          <div className="grid gap-3">
            {ASSISTANT_MODES.map((option) => (
              <button
                key={option.value}
                onClick={() => setProfile({ ...profile, assistant_mode: option.value })}
                className={`rounded-xl border p-3 text-left transition-colors ${
                  profile.assistant_mode === option.value
                    ? "border-oracle-accent bg-oracle-accent/10"
                    : "border-oracle-border hover:border-oracle-muted"
                }`}
              >
                <p className="text-sm font-medium text-oracle-text">{option.label}</p>
                <p className="mt-1 text-xs text-oracle-muted">{option.desc}</p>
              </button>
            ))}
          </div>
        </Card>

        <Card title="Riesgo y horizonte" icon={<Target className="h-4 w-4 text-oracle-accent" />}>
          <div className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-3">
              {RISK_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setProfile({ ...profile, risk_tolerance: option.value })}
                  className={`rounded-xl border p-3 text-left transition-colors ${
                    profile.risk_tolerance === option.value
                      ? "border-oracle-accent bg-oracle-accent/10"
                      : "border-oracle-border hover:border-oracle-muted"
                  }`}
                >
                  <p className="text-sm font-medium text-oracle-text">{option.label}</p>
                  <p className="mt-1 text-xs text-oracle-muted">{option.desc}</p>
                </button>
              ))}
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              {HORIZON_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() =>
                    setProfile({
                      ...profile,
                      investment_horizon: option.value,
                      default_horizon: option.value,
                    })
                  }
                  className={`rounded-xl border p-3 text-left transition-colors ${
                    profile.investment_horizon === option.value
                      ? "border-oracle-accent bg-oracle-accent/10"
                      : "border-oracle-border hover:border-oracle-muted"
                  }`}
                >
                  <p className="text-sm font-medium text-oracle-text">{option.label}</p>
                  <p className="mt-1 text-xs text-oracle-muted">{option.desc}</p>
                </button>
              ))}
            </div>
          </div>
        </Card>

        <Card title="Inbox" icon={<Bell className="h-4 w-4 text-oracle-accent" />}>
          <div className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-2">
              {INBOX_SCOPE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setProfile({ ...profile, inbox_scope_preference: option.value })}
                  className={`rounded-xl border p-3 text-left text-sm transition-colors ${
                    profile.inbox_scope_preference === option.value
                      ? "border-oracle-accent bg-oracle-accent/10 text-oracle-text"
                      : "border-oracle-border text-oracle-muted hover:text-oracle-text"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <div>
              <p className="text-xs text-oracle-muted">Frecuencia de notificaciones</p>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                {NOTIFICATION_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setProfile({ ...profile, notification_frequency: option.value })}
                    className={`rounded-xl border p-3 text-left text-sm transition-colors ${
                      profile.notification_frequency === option.value
                        ? "border-oracle-accent bg-oracle-accent/10 text-oracle-text"
                        : "border-oracle-border text-oracle-muted hover:text-oracle-text"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Card>

        <Card title="MyInvestIA Bot" icon={<Bot className="h-4 w-4 text-oracle-accent" />} className="xl:col-span-2">
          <div className="space-y-4">
            <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                      botStatus.connected
                        ? "bg-oracle-green/15 text-oracle-green"
                        : botStatus.status === "pending"
                          ? "bg-oracle-yellow/15 text-oracle-yellow"
                          : "bg-oracle-border text-oracle-muted"
                    }`}>
                      {botStatus.connected
                        ? "Conectado"
                        : botStatus.status === "pending"
                          ? "Pendiente"
                          : "Desconectado"}
                    </span>
                    {botStatus.bot_username && (
                      <span className="text-xs text-oracle-muted">@{botStatus.bot_username}</span>
                    )}
                    {botStatus.chat_name && (
                      <span className="text-xs text-oracle-muted">Chat: {botStatus.chat_name}</span>
                    )}
                  </div>
                  <div>
                    <h4 className="text-base font-semibold text-oracle-text">Bot personal de avisos para tu cuenta</h4>
                    <p className="text-sm text-oracle-muted">
                      Te manda prioridades del inbox, riesgos de cartera, catalizadores, tesis en riesgo y señales buy/sell de tus activos.
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => void runBotAction("refresh", loadBotStatus)}
                    disabled={botBusy !== null}
                    className="inline-flex items-center gap-2 rounded-xl border border-oracle-border px-3 py-2 text-sm text-oracle-text transition-colors hover:border-oracle-accent disabled:opacity-50"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Refresh
                  </button>
                  <button
                    onClick={() =>
                      void runBotAction("provision", async () => {
                        const result = await postAPI<PersonalBotProvisionResponse>(
                          "/api/v1/notifications/bot/provision-defaults",
                          {},
                        );
                        setBotResult(
                          result.success ? "success" : "error",
                          result.message,
                          result.status,
                        );
                      })
                    }
                    disabled={botBusy !== null || !botStatus.available}
                    className="inline-flex items-center gap-2 rounded-xl border border-oracle-accent/30 bg-oracle-accent/10 px-3 py-2 text-sm text-oracle-accent transition-colors hover:bg-oracle-accent/20 disabled:opacity-50"
                  >
                    <Bell className="h-4 w-4" />
                    Reglas por defecto
                  </button>
                  <button
                    onClick={() =>
                      void runBotAction("run", async () => {
                        const result = await postAPI<PersonalBotRunResponse>(
                          "/api/v1/notifications/bot/run",
                          {},
                        );
                        setBotResult(
                          result.success || result.skipped ? "success" : "error",
                          result.message,
                          result.status,
                        );
                      })
                    }
                    disabled={botBusy !== null || !botStatus.connected}
                    className="inline-flex items-center gap-2 rounded-xl border border-oracle-green/30 bg-oracle-green/10 px-3 py-2 text-sm text-oracle-green transition-colors hover:bg-oracle-green/20 disabled:opacity-50"
                  >
                    <Send className="h-4 w-4" />
                    Ejecutar ahora
                  </button>
                </div>
              </div>

              {botLoading ? (
                <p className="mt-4 text-sm text-oracle-muted">Cargando estado del bot...</p>
              ) : !botStatus.available ? (
                <p className="mt-4 text-sm text-oracle-muted">
                  El servidor todavia no tiene configurado el bot compartido de Telegram. En cuanto exista `TELEGRAM_BOT_TOKEN`, podras conectarlo aqui.
                </p>
              ) : !botStatus.connected ? (
                <div className="mt-4 grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
                  <div className="rounded-2xl border border-oracle-border bg-oracle-panel p-4">
                    <p className="text-sm font-medium text-oracle-text">Conecta tu chat</p>
                    <ol className="mt-2 space-y-2 text-sm text-oracle-muted">
                      <li>1. Pulsa en <span className="text-oracle-text">Generar enlace</span>.</li>
                      <li>2. Abre Telegram y pulsa <span className="text-oracle-text">Start</span>.</li>
                      <li>3. Vuelve aqui y pulsa <span className="text-oracle-text">Verificar</span>.</li>
                    </ol>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        onClick={() =>
                          void runBotAction("connect", async () => {
                            const status = await postAPI<PersonalBotStatus>(
                              "/api/v1/notifications/bot/connect",
                              {},
                            );
                            setBotResult("success", "Enlace generado. Abre Telegram y pulsa Start.", status);
                          })
                        }
                        disabled={botBusy !== null}
                        className="inline-flex items-center gap-2 rounded-xl border border-oracle-accent/30 bg-oracle-accent/10 px-3 py-2 text-sm text-oracle-accent transition-colors hover:bg-oracle-accent/20 disabled:opacity-50"
                      >
                        <Link2 className="h-4 w-4" />
                        Generar enlace
                      </button>
                      <button
                        onClick={() =>
                          void runBotAction("verify", async () => {
                            const result = await postAPI<PersonalBotActionResponse>(
                              "/api/v1/notifications/bot/verify",
                              {},
                            );
                            setBotResult(
                              result.success ? "success" : "error",
                              result.message,
                              result.status,
                            );
                          })
                        }
                        disabled={botBusy !== null || !botStatus.pending_code}
                        className="inline-flex items-center gap-2 rounded-xl border border-oracle-green/30 bg-oracle-green/10 px-3 py-2 text-sm text-oracle-green transition-colors hover:bg-oracle-green/20 disabled:opacity-50"
                      >
                        <RefreshCw className="h-4 w-4" />
                        Verificar
                      </button>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-oracle-border bg-oracle-panel p-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-oracle-muted">Conexion pendiente</p>
                    <div className="mt-3 space-y-2 text-sm">
                      <div>
                        <p className="text-xs text-oracle-muted">Codigo</p>
                        <div className="mt-1 rounded-xl border border-oracle-border bg-oracle-bg/70 px-3 py-2 font-mono text-oracle-text">
                          {botStatus.pending_code ?? "Genera un enlace primero"}
                        </div>
                      </div>
                      <div>
                        <p className="text-xs text-oracle-muted">Caduca</p>
                        <p className="mt-1 text-oracle-text">{formatTimestamp(botStatus.pending_expires_at)}</p>
                      </div>
                      {botStatus.connect_url && (
                        <a
                          href={botStatus.connect_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-2 text-sm font-medium text-oracle-accent hover:underline"
                        >
                          Abrir Telegram
                          <Link2 className="h-4 w-4" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mt-4 space-y-4">
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="rounded-2xl border border-oracle-border bg-oracle-panel p-4">
                      <p className="text-xs uppercase tracking-[0.28em] text-oracle-muted">Ultima entrega</p>
                      <p className="mt-2 text-sm text-oracle-text">{formatTimestamp(botStatus.last_delivery_at)}</p>
                      <p className="mt-1 text-xs text-oracle-muted">
                        {botStatus.last_message_count} mensajes · {botStatus.last_alert_count} alertas
                      </p>
                    </div>
                    <div className="rounded-2xl border border-oracle-border bg-oracle-panel p-4">
                      <p className="text-xs uppercase tracking-[0.28em] text-oracle-muted">Cadencia</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {BOT_CADENCE_OPTIONS.map((minutes) => (
                          <button
                            key={minutes}
                            onClick={() => void updateBotConfig({ cadence_minutes: minutes })}
                            disabled={botBusy !== null}
                            className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                              botStatus.cadence_minutes === minutes
                                ? "border-oracle-accent bg-oracle-accent/10 text-oracle-accent"
                                : "border-oracle-border text-oracle-muted hover:text-oracle-text"
                            }`}
                          >
                            {minutes < 60 ? `${minutes}m` : `${minutes / 60}h`}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-2xl border border-oracle-border bg-oracle-panel p-4">
                      <p className="text-xs uppercase tracking-[0.28em] text-oracle-muted">Umbral</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {BOT_SEVERITY_OPTIONS.map((option) => (
                          <button
                            key={option.value}
                            onClick={() => void updateBotConfig({ min_severity: option.value })}
                            disabled={botBusy !== null}
                            className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                              botStatus.min_severity === option.value
                                ? "border-oracle-accent bg-oracle-accent/10 text-oracle-accent"
                                : "border-oracle-border text-oracle-muted hover:text-oracle-text"
                            }`}
                          >
                            {option.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => void updateBotConfig({ enabled: !botStatus.enabled })}
                      disabled={botBusy !== null}
                      className={`rounded-xl border px-3 py-2 text-sm transition-colors ${
                        botStatus.enabled
                          ? "border-oracle-green/30 bg-oracle-green/10 text-oracle-green"
                          : "border-oracle-border text-oracle-text"
                      }`}
                    >
                      {botStatus.enabled ? "Bot activo" : "Bot pausado"}
                    </button>
                    <button
                      onClick={() =>
                        void runBotAction("test", async () => {
                          const result = await postAPI<PersonalBotActionResponse>(
                            "/api/v1/notifications/bot/test",
                            {},
                          );
                          setBotResult(
                            result.success ? "success" : "error",
                            result.message,
                            result.status,
                          );
                        })
                      }
                      disabled={botBusy !== null}
                      className="rounded-xl border border-oracle-accent/30 bg-oracle-accent/10 px-3 py-2 text-sm text-oracle-accent transition-colors hover:bg-oracle-accent/20 disabled:opacity-50"
                    >
                      Enviar test
                    </button>
                    <button
                      onClick={() =>
                        void runBotAction("disconnect", async () => {
                          const result = await postAPI<PersonalBotActionResponse>(
                            "/api/v1/notifications/bot/disconnect",
                            {},
                          );
                          setBotResult(
                            result.success ? "success" : "error",
                            result.message,
                            result.status,
                          );
                        })
                      }
                      disabled={botBusy !== null}
                      className="rounded-xl border border-oracle-red/30 bg-oracle-red/10 px-3 py-2 text-sm text-oracle-red transition-colors hover:bg-oracle-red/20 disabled:opacity-50"
                    >
                      Desconectar
                    </button>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {BOT_SIGNAL_OPTIONS.map((option) => (
                      <button
                        key={option.key}
                        onClick={() => toggleBotOption(option.key)}
                        disabled={botBusy !== null}
                        className={`rounded-2xl border p-4 text-left transition-colors ${
                          botStatus[option.key]
                            ? "border-oracle-accent bg-oracle-accent/10"
                            : "border-oracle-border hover:border-oracle-border-hover"
                        }`}
                      >
                        <p className="text-sm font-medium text-oracle-text">{option.label}</p>
                        <p className="mt-1 text-xs text-oracle-muted">{option.desc}</p>
                      </button>
                    ))}
                  </div>

                  <div className="rounded-2xl border border-oracle-border bg-oracle-panel p-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-oracle-muted">Historial reciente</p>
                    <div className="mt-3 space-y-2">
                      {botStatus.history.length === 0 ? (
                        <p className="text-sm text-oracle-muted">Todavia no hay ejecuciones registradas.</p>
                      ) : (
                        botStatus.history.slice(0, 5).map((entry) => (
                          <div key={entry.id} className="rounded-xl border border-oracle-border bg-oracle-bg/50 px-3 py-2">
                            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                              <div>
                                <p className="text-sm text-oracle-text">{entry.summary || "Envio del bot"}</p>
                                <p className="text-xs text-oracle-muted">
                                  {entry.reason || "manual"} · {formatTimestamp(entry.started_at)}
                                </p>
                              </div>
                              <span className={`rounded-full px-2 py-0.5 text-[11px] ${
                                entry.status === "success"
                                  ? "bg-oracle-green/15 text-oracle-green"
                                  : entry.status === "skipped"
                                    ? "bg-oracle-yellow/15 text-oracle-yellow"
                                    : "bg-oracle-red/15 text-oracle-red"
                              }`}>
                                {entry.status}
                              </span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}

              {botFeedback && (
                <p className={`mt-4 text-sm ${
                  botFeedback.type === "success" ? "text-oracle-green" : "text-oracle-red"
                }`}>
                  {botFeedback.text}
                </p>
              )}
              {botStatus.last_error && (
                <p className="mt-2 text-xs text-oracle-red">{botStatus.last_error}</p>
              )}
            </div>
          </div>
        </Card>

        <Card title="Objetivos" icon={<Target className="h-4 w-4 text-oracle-accent" />}>
          <div className="flex flex-wrap gap-2">
            {GOAL_PRESETS.map((goal) => (
              <button
                key={goal}
                onClick={() => toggleGoal(goal)}
                className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                  profile.goals.includes(goal)
                    ? "border-oracle-accent bg-oracle-accent/10 text-oracle-accent"
                    : "border-oracle-border text-oracle-muted hover:text-oracle-text"
                }`}
              >
                {goal}
              </button>
            ))}
          </div>
        </Card>

        <Card title="Idioma y moneda" icon={<Globe className="h-4 w-4 text-oracle-accent" />}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs text-oracle-muted">Idioma</p>
              <select
                value={profile.language}
                onChange={(event) => setProfile({ ...profile, language: event.target.value })}
                className="mt-1 w-full rounded-xl border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-oracle-text"
              >
                <option value="es">Español</option>
                <option value="en">English</option>
              </select>
            </div>
            <div>
              <p className="text-xs text-oracle-muted">Moneda preferida</p>
              <select
                value={profile.preferred_currency}
                onChange={(event) => setProfile({ ...profile, preferred_currency: event.target.value })}
                className="mt-1 w-full rounded-xl border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-oracle-text"
              >
                <option value="EUR">EUR (€)</option>
                <option value="USD">USD ($)</option>
                <option value="GBP">GBP (£)</option>
                <option value="CHF">CHF</option>
                <option value="JPY">JPY (¥)</option>
              </select>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
