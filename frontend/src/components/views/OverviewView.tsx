"use client";

import { ArrowRight, BellRing, BriefcaseBusiness, CalendarClock, Compass, Sparkles } from "lucide-react";

import PortfolioSummary from "@/components/dashboard/PortfolioSummary";
import MarketOverviewCard from "@/components/dashboard/MarketOverviewCard";
import BreakingNewsFeed from "@/components/dashboard/BreakingNewsFeed";
import { useInbox } from "@/hooks/useInbox";
import { useBriefing } from "@/hooks/useBriefing";
import { useView } from "@/contexts/ViewContext";
import { getInboxStateLabel } from "@/lib/presentation";
import useLanguageStore from "@/stores/useLanguageStore";

export default function OverviewView() {
  const { data: inbox } = useInbox();
  const { data: briefing } = useBriefing();
  const { openAssetDetail, setActiveSection, setSelectedSymbol } = useView();
  const language = useLanguageStore((state) => state.language);
  const topItems = inbox?.items.slice(0, 3) ?? [];
  const nextEvents = briefing?.next_events?.slice(0, 3) ?? [];

  return (
    <div className="space-y-4">
      <section className="oracle-hero-surface rounded-2xl border border-oracle-border p-5">
        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <div>
            <span className="rounded-full border border-oracle-accent/30 bg-oracle-accent/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-oracle-accent">
              Inicio
            </span>
            <h2 className="mt-3 text-2xl font-semibold text-oracle-text">Empieza por lo importante, no por veinte pantallas</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-oracle-muted">
              Aquí ves primero qué está pasando, por qué importa y por dónde seguir. La profundidad sigue existiendo, pero ya no es lo primero que te cae encima.
            </p>
            <div className="mt-4 rounded-2xl border border-oracle-border bg-oracle-bg/60 p-4">
              <p className="text-[11px] uppercase tracking-wide text-oracle-muted">Resumen breve</p>
              <p className="mt-2 text-sm leading-6 text-oracle-text">
                {briefing?.briefing?.split("\n").slice(0, 4).join(" ") || "Generando briefing..."}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {(briefing?.suggestions ?? []).slice(0, 4).map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      if (suggestion.toLowerCase().includes("terminal")) {
                        openAssetDetail();
                      } else if (suggestion.toLowerCase().includes("macro")) {
                        setActiveSection("markets", "markets-macro");
                      } else {
                        setActiveSection("priorities");
                      }
                    }}
                    className="rounded-full border border-oracle-border px-2.5 py-1 text-xs text-oracle-text transition-colors hover:bg-oracle-panel-hover"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3">
            <button
              onClick={() => setActiveSection("priorities")}
              className="rounded-2xl border border-oracle-accent/35 bg-oracle-accent/12 p-4 text-left transition-colors hover:bg-oracle-accent/18"
            >
              <p className="text-[11px] uppercase tracking-wide text-oracle-accent">Prioridades</p>
              <p className="mt-2 text-lg font-semibold text-oracle-text">{inbox?.total ?? 0} cosas para mirar ahora</p>
              <p className="mt-1 text-sm text-oracle-muted">Riesgo, eventos y oportunidades ya ordenados.</p>
            </button>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => openAssetDetail()}
                className="rounded-2xl border border-oracle-border bg-oracle-bg/60 p-4 text-left transition-colors hover:bg-oracle-bg"
              >
                <Compass className="h-4 w-4 text-oracle-accent" />
                <p className="mt-2 text-sm font-semibold text-oracle-text">Detalle activo</p>
                <p className="mt-1 text-xs text-oracle-muted">Profundiza en un símbolo</p>
              </button>
              <button
                onClick={() => setActiveSection("portfolio", "portfolio-theses")}
                className="rounded-2xl border border-oracle-border bg-oracle-bg/60 p-4 text-left transition-colors hover:bg-oracle-bg"
              >
                <BriefcaseBusiness className="h-4 w-4 text-oracle-accent" />
                <p className="mt-2 text-sm font-semibold text-oracle-text">Cartera</p>
                <p className="mt-1 text-xs text-oracle-muted">Posiciones, riesgo y tesis</p>
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setActiveSection("research")}
                className="rounded-2xl border border-oracle-border bg-oracle-bg/60 p-4 text-left transition-colors hover:bg-oracle-bg"
              >
                <Sparkles className="h-4 w-4 text-oracle-accent" />
                <p className="mt-2 text-sm font-semibold text-oracle-text">Investigación</p>
                <p className="mt-1 text-xs text-oracle-muted">Ideas, factores y señal IA</p>
              </button>
              <button
                onClick={() => setActiveSection("assistant")}
                className="rounded-2xl border border-oracle-border bg-oracle-bg/60 p-4 text-left transition-colors hover:bg-oracle-bg"
              >
                <BellRing className="h-4 w-4 text-oracle-accent" />
                <p className="mt-2 text-sm font-semibold text-oracle-text">Asistente</p>
                <p className="mt-1 text-xs text-oracle-muted">Chat, bot y alertas</p>
              </button>
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-oracle-border bg-oracle-panel">
          <div className="border-b border-oracle-border px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">Top 3 prioridades</p>
            <p className="mt-1 text-sm text-oracle-muted">Lo que merece atención antes de profundizar.</p>
          </div>
          <div className="space-y-3 p-4">
            {topItems.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  if (item.primary_symbol) setSelectedSymbol(item.primary_symbol);
                  setActiveSection("priorities");
                }}
                className="w-full rounded-xl border border-oracle-border bg-oracle-bg/40 p-4 text-left transition-colors hover:bg-oracle-bg"
              >
                <div className="flex items-center gap-2">
                  <span className="rounded-full border border-oracle-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-oracle-muted">
                    {getInboxStateLabel(item.state, language)}
                  </span>
                  <span className="ml-auto text-xs font-mono text-oracle-accent">{item.priority_score.toFixed(0)}</span>
                </div>
                <p className="mt-3 text-sm font-semibold text-oracle-text">{item.title}</p>
                <p className="mt-1 text-xs leading-5 text-oracle-muted">{item.why_now || item.summary}</p>
                <div className="mt-3 inline-flex items-center gap-1 text-xs text-oracle-accent">
                  Ver detalle
                  <ArrowRight className="h-3.5 w-3.5" />
                </div>
              </button>
            ))}
            {topItems.length === 0 ? <p className="text-sm text-oracle-muted">Aún no hay prioridades activas.</p> : null}
          </div>
        </section>

        <section className="rounded-2xl border border-oracle-border bg-oracle-panel">
          <div className="border-b border-oracle-border px-4 py-3">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
              <CalendarClock className="h-3.5 w-3.5" />
              Próximos eventos
            </div>
            <p className="mt-1 text-sm text-oracle-muted">Lo próximo que puede mover el día.</p>
          </div>
          <div className="space-y-3 p-4">
            {nextEvents.map((event) => (
              <div key={event.id} className="rounded-xl border border-oracle-border bg-oracle-bg/40 p-4">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-oracle-muted">
                  <span>{event.event_type}</span>
                  <span>{event.importance}</span>
                  {event.symbol ? <span className="font-mono text-oracle-accent">{event.symbol}</span> : null}
                </div>
                <p className="mt-2 text-sm font-semibold text-oracle-text">{event.title}</p>
                <p className="mt-1 text-xs leading-5 text-oracle-muted">{event.description}</p>
              </div>
            ))}
            {nextEvents.length === 0 ? <p className="text-sm text-oracle-muted">No hay eventos próximos todavía.</p> : null}
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-4">
          <PortfolioSummary />
          <MarketOverviewCard />
        </div>
        <BreakingNewsFeed defaultCollapsed={false} />
      </div>
    </div>
  );
}
