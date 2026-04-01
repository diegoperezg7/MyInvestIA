"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Bell,
  Bookmark,
  Clock3,
  ExternalLink,
  EyeOff,
  FilePenLine,
  RefreshCw,
  Send,
} from "lucide-react";

import { useInbox } from "@/hooks/useInbox";
import { useTheses } from "@/hooks/useTheses";
import { postAPI } from "@/lib/api";
import {
  getAssistantModeLabel,
  getConfidenceBand,
  getHorizonLabel,
  getImpactLabel,
  getInboxKindLabel,
  getInboxScopeLabel,
  getInboxStateLabel,
  getInboxStatusLabel,
} from "@/lib/presentation";
import type { InboxItem } from "@/types";
import { useView } from "@/contexts/ViewContext";
import useLanguageStore from "@/stores/useLanguageStore";

const FILTERS = [
  { label: "Mi cartera", patch: { scope: "portfolio" } },
  { label: "Seguimiento", patch: { scope: "watchlist" } },
  { label: "Macro", patch: { scope: "macro" } },
  { label: "Investigación", patch: { scope: "research" } },
  { label: "Guardado", patch: { status: "saved" } },
  { label: "Descartado", patch: { status: "dismissed" } },
  { label: "Confirmado", patch: { status: "confirmed" } },
  { label: "Por confirmar", patch: { status: "exploratory" } },
];

function badgeTone(item: InboxItem) {
  if (item.state === "confirmed") {
    return "border-oracle-green/30 bg-oracle-green/10 text-oracle-green";
  }
  return "border-oracle-yellow/30 bg-oracle-yellow/10 text-oracle-yellow";
}

function priorityTone(score: number) {
  if (score >= 75) return "text-oracle-red";
  if (score >= 55) return "text-oracle-yellow";
  return "text-oracle-accent";
}

function timeAgo(value: string) {
  const diff = Date.now() - new Date(value).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "ahora";
  if (mins < 60) return `hace ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${Math.floor(hours / 24)}d`;
}

export default function InboxView() {
  const { data, loading, error, filters, setFilters, refresh, mutateItem, reload } = useInbox();
  const { createFromInbox } = useTheses();
  const { openAssetDetail, setActiveSection, setSelectedSymbol } = useView();
  const language = useLanguageStore((state) => state.language);
  const [selectedId, setSelectedId] = useState<string>("");
  const [creatingAlert, setCreatingAlert] = useState(false);

  useEffect(() => {
    if (data?.items[0] && !selectedId) {
      setSelectedId(data.items[0].id);
    }
    if (selectedId && data && !data.items.some((item) => item.id === selectedId)) {
      setSelectedId(data.items[0]?.id ?? "");
    }
  }, [data, selectedId]);

  const selectedItem = useMemo(
    () => data?.items.find((item) => item.id === selectedId) ?? data?.items[0] ?? null,
    [data, selectedId]
  );

  const handleCreateAlert = async (item: InboxItem) => {
    if (!item.primary_symbol) return;
    try {
      setCreatingAlert(true);
      await postAPI("/api/v1/alerts/rules", {
        name: `${item.primary_symbol} ${item.kind} monitor`,
        symbols: [item.primary_symbol],
        cooldown_minutes: 120,
        delivery_channels: ["telegram"],
        active: true,
        linked_thesis_id: item.linked_thesis_id,
        conditions: [
          {
            field: "symbol",
            operator: "contains",
            value: item.primary_symbol,
            source: "inbox",
          },
        ],
      });
    } finally {
      setCreatingAlert(false);
    }
  };

  return (
    <div className="space-y-4">
      <section className="oracle-hero-surface rounded-2xl border border-oracle-border p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <span className="rounded-full border border-oracle-accent/30 bg-oracle-accent/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-oracle-accent">
              Prioridades
            </span>
            <h2 className="mt-3 text-2xl font-semibold text-oracle-text">Qué merece atención ahora</h2>
            <p className="mt-1 max-w-3xl text-sm text-oracle-muted">
              Aquí unimos riesgo, noticias, eventos y oportunidades en una sola bandeja. El detalle por activo sigue existiendo, pero primero decides qué importa.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-oracle-border bg-oracle-bg/60 px-4 py-3 text-sm">
              <p className="text-oracle-muted">Items activos</p>
              <p className="mt-1 text-lg font-semibold text-oracle-text">{data?.total ?? 0}</p>
            </div>
            <button
              onClick={() => refresh()}
              className="inline-flex items-center gap-2 rounded-xl border border-oracle-accent/30 bg-oracle-accent/15 px-4 py-3 text-sm font-medium text-oracle-accent transition-colors hover:bg-oracle-accent/25"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Actualizar
            </button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={() => setFilters({})}
            className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
              Object.keys(filters).length === 0
                ? "border-oracle-accent/40 bg-oracle-accent/20 text-oracle-accent"
                : "border-oracle-border text-oracle-muted hover:text-oracle-text"
            }`}
          >
            Todo
          </button>
          {FILTERS.map((filter) => {
            const active = Object.entries(filter.patch).every(
              ([key, value]) => filters[key as keyof typeof filters] === value
            );
            return (
              <button
                key={filter.label}
                onClick={() => setFilters(filter.patch)}
                className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                  active
                    ? "border-oracle-accent/40 bg-oracle-accent/20 text-oracle-accent"
                    : "border-oracle-border text-oracle-muted hover:text-oracle-text"
                }`}
              >
                {filter.label}
              </button>
            );
          })}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.92fr_1.08fr]">
        <section className="rounded-2xl border border-oracle-border bg-oracle-panel">
          <div className="flex items-center justify-between border-b border-oracle-border px-4 py-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">Bandeja</p>
              <p className="mt-1 text-sm text-oracle-muted">
                {data?.generated_at ? `Actualizado ${timeAgo(data.generated_at)}` : "Pendiente"}
              </p>
            </div>
            <button
              onClick={() => reload(filters, true)}
              className="rounded-lg border border-oracle-border px-2.5 py-1 text-xs text-oracle-muted transition-colors hover:text-oracle-text"
            >
              Recalcular
            </button>
          </div>

          <div className="max-h-[72vh] overflow-y-auto p-3">
            {loading && !data ? (
              <div className="space-y-3">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div key={index} className="animate-pulse rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                    <div className="h-3 w-24 rounded bg-oracle-border" />
                    <div className="mt-3 h-4 w-2/3 rounded bg-oracle-border" />
                    <div className="mt-2 h-3 w-full rounded bg-oracle-border" />
                  </div>
                ))}
              </div>
            ) : null}

            {!loading && data?.items.length === 0 ? (
              <div className="rounded-xl border border-dashed border-oracle-border p-6 text-center">
                <p className="text-sm text-oracle-text">No hay items para este filtro.</p>
                <p className="mt-1 text-xs text-oracle-muted">
                  Si no tienes portfolio ni watchlist, la app debería caer a macro y oportunidades de mercado al refrescar.
                </p>
              </div>
            ) : null}

            <div className="space-y-3">
              {data?.items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  className={`w-full rounded-xl border p-4 text-left transition-colors ${
                    selectedItem?.id === item.id
                      ? "border-oracle-accent/50 bg-oracle-accent/10"
                      : "border-oracle-border bg-oracle-bg/40 hover:bg-oracle-bg"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${badgeTone(item)}`}>
                      {getInboxStateLabel(item.state, language)}
                    </span>
                    <span className="rounded-full border border-oracle-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-oracle-muted">
                      {getInboxScopeLabel(item.scope, language)}
                    </span>
                    <span className={`ml-auto text-xs font-mono ${priorityTone(item.priority_score)}`}>
                      {item.priority_score.toFixed(0)}
                    </span>
                  </div>
                  <h3 className="mt-3 text-sm font-semibold text-oracle-text">{item.title}</h3>
                  <p className="mt-2 line-clamp-2 text-xs leading-5 text-oracle-muted">{item.summary}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-oracle-muted">
                    {item.symbols.slice(0, 3).map((symbol) => (
                      <span key={`${item.id}-${symbol}`} className="rounded bg-oracle-accent/10 px-1.5 py-0.5 font-mono text-oracle-accent">
                        {symbol}
                      </span>
                    ))}
                    <span>
                      fiabilidad {getConfidenceBand(item.confidence, language).toLowerCase()}{" "}
                      {Math.round(item.confidence * 100)}%
                    </span>
                    <span>horizonte {getHorizonLabel(item.horizon, language).toLowerCase()}</span>
                    <span>{timeAgo(item.updated_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-oracle-border bg-oracle-panel">
          <div className="border-b border-oracle-border px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">Detalle</p>
            <p className="mt-1 text-sm text-oracle-muted">Qué pasa, por qué importa y qué harías ahora.</p>
          </div>

          {selectedItem ? (
            <div className="space-y-5 p-5">
              <div className="flex flex-wrap items-start gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${badgeTone(selectedItem)}`}>
                      {getInboxStateLabel(selectedItem.state, language)}
                    </span>
                    <span className="rounded-full border border-oracle-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-oracle-muted">
                      {getInboxKindLabel(selectedItem.kind, language)}
                    </span>
                  </div>
                  <h3 className="mt-3 text-xl font-semibold text-oracle-text">{selectedItem.title}</h3>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-oracle-muted">{selectedItem.summary}</p>
                </div>
                <div className="ml-auto rounded-2xl border border-oracle-border bg-oracle-bg/60 px-4 py-3">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Prioridad</p>
                  <p className={`mt-1 text-2xl font-semibold ${priorityTone(selectedItem.priority_score)}`}>
                    {selectedItem.priority_score.toFixed(0)}
                  </p>
                  <p className="text-xs text-oracle-muted">
                    Fiabilidad {getConfidenceBand(selectedItem.confidence, language).toLowerCase()}{" "}
                    {Math.round(selectedItem.confidence * 100)}%
                  </p>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Qué pasa</p>
                  <p className="mt-2 text-sm leading-6 text-oracle-text">{selectedItem.why_now || "Todavía esperamos confirmación adicional."}</p>
                </div>
                <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Por qué importa</p>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full border border-oracle-border px-2 py-1 text-oracle-text">
                      impacto {getImpactLabel(selectedItem.impact, language).toLowerCase()}
                    </span>
                    <span className="rounded-full border border-oracle-border px-2 py-1 text-oracle-text">
                      horizonte {getHorizonLabel(selectedItem.horizon, language).toLowerCase()}
                    </span>
                    <span className="rounded-full border border-oracle-border px-2 py-1 text-oracle-text">
                      estado {getInboxStatusLabel(selectedItem.status, language).toLowerCase()}
                    </span>
                    <span className="rounded-full border border-oracle-border px-2 py-1 text-oracle-text">
                      lectura {getAssistantModeLabel(selectedItem.assistant_mode, language).toLowerCase()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => mutateItem(selectedItem.id, "save")}
                  className="inline-flex items-center gap-2 rounded-lg border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-sm text-oracle-text transition-colors hover:bg-oracle-bg"
                >
                  <Bookmark className="h-4 w-4" />
                  Guardar
                </button>
                <button
                  onClick={() => mutateItem(selectedItem.id, "dismiss")}
                  className="inline-flex items-center gap-2 rounded-lg border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-sm text-oracle-text transition-colors hover:bg-oracle-bg"
                >
                  <EyeOff className="h-4 w-4" />
                  Descartar
                </button>
                <button
                  onClick={() => mutateItem(selectedItem.id, "snooze")}
                  className="inline-flex items-center gap-2 rounded-lg border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-sm text-oracle-text transition-colors hover:bg-oracle-bg"
                >
                  <Clock3 className="h-4 w-4" />
                  Posponer
                </button>
                <button
                  onClick={async () => {
                    const result = await createFromInbox(selectedItem.id);
                    setActiveSection("portfolio", "portfolio-theses");
                    await reload(filters, true);
                    setSelectedSymbol(result.thesis.symbol);
                  }}
                  className="inline-flex items-center gap-2 rounded-lg border border-oracle-accent/30 bg-oracle-accent/15 px-3 py-2 text-sm text-oracle-accent transition-colors hover:bg-oracle-accent/20"
                >
                  <FilePenLine className="h-4 w-4" />
                  Crear tesis
                </button>
                <button
                  onClick={() => handleCreateAlert(selectedItem)}
                  disabled={creatingAlert || !selectedItem.primary_symbol}
                  className="inline-flex items-center gap-2 rounded-lg border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-sm text-oracle-text transition-colors hover:bg-oracle-bg disabled:opacity-50"
                >
                  <Bell className="h-4 w-4" />
                  Crear alerta
                </button>
                <button
                  onClick={() => {
                    if (selectedItem.primary_symbol) {
                      setSelectedSymbol(selectedItem.primary_symbol);
                      openAssetDetail(selectedItem.primary_symbol);
                      return;
                    }
                    openAssetDetail();
                  }}
                  className="inline-flex items-center gap-2 rounded-lg border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-sm text-oracle-text transition-colors hover:bg-oracle-bg"
                >
                  <Send className="h-4 w-4" />
                  Abrir detalle del activo
                </button>
              </div>

              <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
                <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Qué lo respalda</p>
                  <div className="mt-3 space-y-3">
                    {selectedItem.evidence.map((evidence, index) => (
                      <div key={`${evidence.source}-${index}`} className="rounded-lg border border-oracle-border bg-oracle-panel/60 p-3">
                        <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-oracle-muted">
                          <span>{getInboxKindLabel(evidence.category, language)}</span>
                          <span>{evidence.source}</span>
                          <span className="ml-auto font-mono">fiabilidad {Math.round(evidence.confidence * 100)}%</span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-oracle-text">{evidence.summary}</p>
                        {evidence.url ? (
                          <a
                            href={evidence.url}
                            target="_blank"
                            rel="noreferrer"
                          className="mt-2 inline-flex items-center gap-1 text-xs text-oracle-accent"
                        >
                            Abrir fuente
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                    <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Equilibrio de fuentes</p>
                    <div className="mt-3 space-y-2">
                      {selectedItem.source_breakdown.map((source) => (
                        <div key={source.source} className="flex items-center justify-between rounded-lg border border-oracle-border bg-oracle-panel/60 px-3 py-2 text-sm">
                          <div>
                            <p className="font-medium text-oracle-text">{source.source}</p>
                            <p className="text-xs text-oracle-muted">{source.count} items</p>
                          </div>
                          <div className="text-right">
                            <p className="font-mono text-oracle-text">{(source.weight * 100).toFixed(0)}</p>
                            <p className="text-xs text-oracle-muted">fiabilidad {(source.confidence * 100).toFixed(0)}%</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                    <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Activos relacionados</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {selectedItem.symbols.map((symbol) => (
                        <button
                            key={`${selectedItem.id}-${symbol}`}
                          onClick={() => {
                            setSelectedSymbol(symbol);
                            openAssetDetail(symbol);
                          }}
                          className="rounded-full border border-oracle-accent/25 bg-oracle-accent/10 px-2.5 py-1 font-mono text-xs text-oracle-accent transition-colors hover:bg-oracle-accent/20"
                        >
                          {symbol}
                        </button>
                      ))}
                      {selectedItem.symbols.length === 0 ? (
                        <div className="flex items-center gap-2 text-sm text-oracle-muted">
                          <AlertTriangle className="h-4 w-4" />
                          Idea macro o de cartera, sin un símbolo único
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-sm text-oracle-muted">
              Selecciona un item del inbox para ver detalle y acciones.
            </div>
          )}
          {error ? <p className="px-5 pb-5 text-sm text-oracle-red">{error}</p> : null}
        </section>
      </div>
    </div>
  );
}
