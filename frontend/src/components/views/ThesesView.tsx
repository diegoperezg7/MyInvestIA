"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, FileText, Plus, RefreshCw, ShieldAlert, Target } from "lucide-react";

import { fetchAPI } from "@/lib/api";
import { useTheses } from "@/hooks/useTheses";
import {
  getConfidenceBand,
  getHorizonLabel,
  getThesisReviewStateLabel,
  getThesisStanceLabel,
  getThesisStatusLabel,
} from "@/lib/presentation";
import type { Thesis, ThesisEvent } from "@/types";
import { useView } from "@/contexts/ViewContext";
import useLanguageStore from "@/stores/useLanguageStore";

function reviewTone(state: Thesis["review_state"]) {
  if (state === "broken") return "text-oracle-red";
  if (state === "at_risk") return "text-oracle-yellow";
  return "text-oracle-green";
}

function timeAgo(value: string) {
  const diff = Date.now() - new Date(value).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `hace ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${Math.floor(hours / 24)}d`;
}

export default function ThesesView({ embedded = false }: { embedded?: boolean }) {
  const { data, loading, error, reload, createManual, review, update } = useTheses();
  const { openAssetDetail, setSelectedSymbol } = useView();
  const language = useLanguageStore((state) => state.language);
  const [selectedThesisId, setSelectedThesisId] = useState("");
  const [events, setEvents] = useState<ThesisEvent[]>([]);
  const [reviewNotes, setReviewNotes] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (data?.theses[0] && !selectedThesisId) {
      setSelectedThesisId(data.theses[0].id);
    }
  }, [data, selectedThesisId]);

  const selected = data?.theses.find((thesis) => thesis.id === selectedThesisId) ?? data?.theses[0] ?? null;

  useEffect(() => {
    if (!selected?.id) return;
    fetchAPI<{ events: ThesisEvent[] }>(`/api/v1/theses/${selected.id}/events`)
      .then((result) => setEvents(result.events))
      .catch(() => setEvents([]));
  }, [selected?.id]);

  const handleCreate = async () => {
    try {
      setCreating(true);
      const thesis = await createManual({
        symbol: "SPY",
        stance: "base",
        conviction: 0.5,
        horizon: "medium",
        entry_zone: "",
        invalidation: "",
        catalysts: [],
        risks: [],
        notes: "",
      });
      setSelectedThesisId(thesis.id);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-4">
      {!embedded ? (
        <section className="oracle-hero-surface rounded-2xl border border-oracle-border p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <span className="rounded-full border border-oracle-accent/30 bg-oracle-accent/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-oracle-accent">
                Tesis
              </span>
              <h2 className="mt-3 text-2xl font-semibold text-oracle-text">Ideas con memoria y revisión</h2>
              <p className="mt-1 max-w-3xl text-sm text-oracle-muted">
                Cada tesis guarda postura, invalidación, catalizadores y revisiones. La idea es medir si una tesis mejora o se rompe, no solo mirar el precio.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCreate}
                disabled={creating}
                className="inline-flex items-center gap-2 rounded-xl border border-oracle-border bg-oracle-bg/60 px-4 py-3 text-sm text-oracle-text transition-colors hover:bg-oracle-bg disabled:opacity-50"
              >
                <Plus className="h-4 w-4" />
                Tesis vacía
              </button>
              <button
                onClick={() => reload()}
                className="inline-flex items-center gap-2 rounded-xl border border-oracle-accent/30 bg-oracle-accent/15 px-4 py-3 text-sm font-medium text-oracle-accent transition-colors hover:bg-oracle-accent/25"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                Actualizar
              </button>
            </div>
          </div>
        </section>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-oracle-border bg-oracle-panel p-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">Tesis</p>
            <p className="mt-1 text-sm text-oracle-muted">Ideas activas, revisión y señales de ruptura.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreate}
              disabled={creating}
              className="inline-flex items-center gap-2 rounded-xl border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-sm text-oracle-text transition-colors hover:bg-oracle-bg disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              Nueva tesis
            </button>
            <button
              onClick={() => reload()}
              className="inline-flex items-center gap-2 rounded-xl border border-oracle-accent/30 bg-oracle-accent/15 px-3 py-2 text-sm font-medium text-oracle-accent transition-colors hover:bg-oracle-accent/25"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Actualizar
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.88fr_1.12fr]">
        <section className="rounded-2xl border border-oracle-border bg-oracle-panel">
          <div className="border-b border-oracle-border px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">Tesis activas</p>
            <p className="mt-1 text-sm text-oracle-muted">{data?.total ?? 0} en total</p>
          </div>
          <div className="max-h-[72vh] overflow-y-auto p-3">
            {data?.theses.map((thesis) => (
              <button
                key={thesis.id}
                onClick={() => setSelectedThesisId(thesis.id)}
                className={`mb-3 w-full rounded-xl border p-4 text-left transition-colors ${
                  thesis.id === selected?.id
                    ? "border-oracle-accent/50 bg-oracle-accent/10"
                    : "border-oracle-border bg-oracle-bg/40 hover:bg-oracle-bg"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="rounded-full border border-oracle-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-oracle-muted">
                    {getThesisStanceLabel(thesis.stance, language)}
                  </span>
                  <span className={`ml-auto text-xs uppercase ${reviewTone(thesis.review_state)}`}>
                    {getThesisReviewStateLabel(thesis.review_state, language)}
                  </span>
                </div>
                <h3 className="mt-3 text-lg font-semibold text-oracle-text">{thesis.symbol}</h3>
                <p className="mt-1 text-sm text-oracle-muted">{thesis.notes || "Sin notas todavía."}</p>
                <div className="mt-3 flex items-center gap-2 text-xs text-oracle-muted">
                  <span>
                    {Math.round(thesis.conviction * 100)}% convicción · fiabilidad{" "}
                    {getConfidenceBand(thesis.conviction, language).toLowerCase()}
                  </span>
                  <span>{getHorizonLabel(thesis.horizon, language)}</span>
                  <span>{timeAgo(thesis.updated_at)}</span>
                </div>
              </button>
            ))}
            {!loading && data?.theses.length === 0 ? (
              <div className="rounded-xl border border-dashed border-oracle-border p-6 text-center text-sm text-oracle-muted">
                Crea una tesis desde Prioridades o abre una vacía aquí.
              </div>
            ) : null}
            {error ? <p className="text-sm text-oracle-red">{error}</p> : null}
          </div>
        </section>

        <section className="rounded-2xl border border-oracle-border bg-oracle-panel">
          {selected ? (
            <div className="space-y-5 p-5">
              <div className="flex flex-wrap items-start gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-oracle-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-oracle-muted">
                      {getThesisStatusLabel(selected.status, language)}
                    </span>
                    <span className={`text-xs uppercase ${reviewTone(selected.review_state)}`}>
                      {getThesisReviewStateLabel(selected.review_state, language)}
                    </span>
                  </div>
                  <h3 className="mt-3 text-2xl font-semibold text-oracle-text">{selected.symbol}</h3>
                  <p className="mt-2 text-sm leading-6 text-oracle-muted">{selected.notes || "Sin notas todavía."}</p>
                </div>
                <div className="ml-auto flex gap-2">
                  <button
                    onClick={() => {
                      setSelectedSymbol(selected.symbol);
                      openAssetDetail(selected.symbol);
                    }}
                    className="rounded-lg border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-sm text-oracle-text transition-colors hover:bg-oracle-bg"
                  >
                    Abrir detalle del activo
                  </button>
                  <button
                    onClick={() =>
                      update(selected.id, {
                        status: selected.status === "active" ? "paused" : "active",
                      })
                    }
                    className="rounded-lg border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-sm text-oracle-text transition-colors hover:bg-oracle-bg"
                  >
                    {selected.status === "active" ? "Pausar" : "Reactivar"}
                  </button>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-oracle-muted">
                    <Target className="h-3.5 w-3.5" />
                    Entrada
                  </div>
                  <p className="mt-2 text-sm text-oracle-text">{selected.entry_zone || "No definida"}</p>
                </div>
                <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-oracle-muted">
                    <ShieldAlert className="h-3.5 w-3.5" />
                    Invalida si
                  </div>
                  <p className="mt-2 text-sm text-oracle-text">{selected.invalidation || "No definida"}</p>
                </div>
                <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-oracle-muted">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Convicción
                  </div>
                  <p className="mt-2 text-sm text-oracle-text">{Math.round(selected.conviction * 100)}%</p>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Catalizadores</p>
                  <div className="mt-3 space-y-2">
                    {selected.catalysts.length > 0 ? selected.catalysts.map((catalyst) => (
                      <p key={catalyst} className="rounded-lg border border-oracle-border bg-oracle-panel/60 px-3 py-2 text-sm text-oracle-text">
                        {catalyst}
                      </p>
                    )) : <p className="text-sm text-oracle-muted">Sin catalizadores aún.</p>}
                  </div>
                </div>
                <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                  <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Riesgos</p>
                  <div className="mt-3 space-y-2">
                    {selected.risks.length > 0 ? selected.risks.map((risk) => (
                      <p key={risk} className="rounded-lg border border-oracle-border bg-oracle-panel/60 px-3 py-2 text-sm text-oracle-text">
                        {risk}
                      </p>
                    )) : <p className="text-sm text-oracle-muted">Sin riesgos documentados aún.</p>}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-oracle-muted">
                    <FileText className="h-3.5 w-3.5" />
                    Revisar tesis
                </div>
                <textarea
                  value={reviewNotes}
                  onChange={(event) => setReviewNotes(event.target.value)}
                  rows={4}
                  placeholder="Qué ha cambiado desde la última revisión..."
                  className="mt-3 w-full rounded-xl border border-oracle-border bg-oracle-panel/70 px-3 py-2 text-sm text-oracle-text placeholder:text-oracle-muted"
                />
                <div className="mt-3 flex items-center justify-between gap-3">
                  <p className="text-xs text-oracle-muted">
                    La revisión usa precio vivo, señal técnica y prioridades relacionadas.
                  </p>
                  <button
                    onClick={async () => {
                      await review(selected.id, reviewNotes);
                      setReviewNotes("");
                    }}
                    className="rounded-lg border border-oracle-accent/30 bg-oracle-accent/15 px-3 py-2 text-sm text-oracle-accent transition-colors hover:bg-oracle-accent/20"
                  >
                    Revisar ahora
                  </button>
                </div>
              </div>

              <div className="rounded-xl border border-oracle-border bg-oracle-bg/50 p-4">
                <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Historial</p>
                <div className="mt-3 space-y-3">
                  {events.map((event) => (
                    <div key={event.id} className="rounded-lg border border-oracle-border bg-oracle-panel/60 px-3 py-3">
                      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-oracle-muted">
                        <span>{event.event_type}</span>
                        {event.review_state ? (
                          <span className={reviewTone(event.review_state)}>
                            {getThesisReviewStateLabel(event.review_state, language)}
                          </span>
                        ) : null}
                        <span className="ml-auto">{timeAgo(event.created_at)}</span>
                      </div>
                      <p className="mt-2 text-sm text-oracle-text">{event.summary}</p>
                    </div>
                  ))}
                  {events.length === 0 ? <p className="text-sm text-oracle-muted">Sin eventos todavía.</p> : null}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-sm text-oracle-muted">
              Selecciona una tesis o crea una nueva.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
