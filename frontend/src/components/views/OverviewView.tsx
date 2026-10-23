"use client";

import { ArrowRight, BellRing, BriefcaseBusiness, CalendarClock, Compass, Sparkles } from "lucide-react";

import PortfolioSummary from "@/components/dashboard/PortfolioSummary";
import MarketOverviewCard from "@/components/dashboard/MarketOverviewCard";
import BreakingNewsFeed from "@/components/dashboard/BreakingNewsFeed";
import { useInbox } from "@/hooks/useInbox";
import { useBriefing } from "@/hooks/useBriefing";
import { useView } from "@/contexts/ViewContext";
import { formatInlineDates, getInboxStateLabel } from "@/lib/presentation";
import useLanguageStore from "@/stores/useLanguageStore";

const COPY = {
  es: {
    home: "Inicio",
    heroTitle: "Empieza por lo importante, no por veinte pantallas",
    heroBody: "Aquí ves primero qué está pasando, por qué importa y por dónde seguir. La profundidad sigue existiendo, pero ya no es lo primero que te cae encima.",
    brief: "Resumen breve",
    priorities: "Prioridades",
    prioritiesBody: "Riesgo, eventos y oportunidades ya ordenados.",
    asset: "Detalle activo",
    assetBody: "Profundiza en un símbolo",
    portfolio: "Cartera",
    portfolioBody: "Posiciones, riesgo y tesis",
    research: "Investigación",
    researchBody: "Ideas, factores y señal IA",
    assistant: "Asistente",
    assistantBody: "Chat, bot y alertas",
    top3: "Top 3 prioridades",
    top3Body: "Lo que merece atención antes de profundizar.",
    details: "Ver detalle",
    noPriorities: "Aún no hay prioridades activas.",
    events: "Próximos eventos",
    eventsBody: "Lo próximo que puede mover el día.",
    noEvents: "No hay eventos próximos todavía.",
    thingsToCheck: (n: number) => `${n} cosas para mirar ahora`,
    generating: "Generando briefing...",
  },
  en: {
    home: "Home",
    heroTitle: "Start with what matters, not with twenty screens",
    heroBody: "See what is happening, why it matters and where to go next first. The depth is still there, it just is not the first thing you land on.",
    brief: "Short briefing",
    priorities: "Priorities",
    prioritiesBody: "Risk, events and opportunities, already ranked.",
    asset: "Asset detail",
    assetBody: "Drill into a symbol",
    portfolio: "Portfolio",
    portfolioBody: "Positions, risk and theses",
    research: "Research",
    researchBody: "Ideas, factors and AI signal",
    assistant: "Assistant",
    assistantBody: "Chat, bot and alerts",
    top3: "Top 3 priorities",
    top3Body: "What deserves attention before you dig deeper.",
    details: "View details",
    noPriorities: "No active priorities yet.",
    events: "Upcoming events",
    eventsBody: "What could move the day next.",
    noEvents: "No upcoming events yet.",
    thingsToCheck: (n: number) => `${n} things to check now`,
    generating: "Generating briefing...",
  },
};

export default function OverviewView() {
  const { data: inbox } = useInbox();
  const { data: briefing } = useBriefing();
  const { openAssetDetail, setActiveSection, setSelectedSymbol } = useView();
  const language = useLanguageStore((state) => state.language);
  const c = COPY[language];
  const topItems = inbox?.items.slice(0, 3) ?? [];
  const nextEvents = briefing?.next_events?.slice(0, 3) ?? [];
  // The briefing arrives as markdown: keep the first section's bullet points.
  const briefingLines = (briefing?.briefing?.split("\n## ")[0] ?? "")
    .split("\n")
    .filter((line) => line.trim().startsWith("- "))
    .map((line) => formatInlineDates(line.trim().slice(2), language))
    .slice(0, 4);

  return (
    <div className="space-y-4">
      <section className="oracle-hero-surface rounded-2xl border border-oracle-border p-5">
        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <div>
            <span className="rounded-full border border-oracle-accent/30 bg-oracle-accent/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-oracle-accent">
              {c.home}
            </span>
            <h2 className="mt-3 text-2xl font-semibold text-oracle-text">{c.heroTitle}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-oracle-muted">
              {c.heroBody}
            </p>
            <div className="mt-4 rounded-2xl border border-oracle-border bg-oracle-bg/60 p-4">
              <p className="text-[11px] uppercase tracking-wide text-oracle-muted">{c.brief}</p>
              {briefingLines.length > 0 ? (
                <ul className="mt-2 space-y-1.5 text-sm leading-6 text-oracle-text">
                  {briefingLines.map((line) => (
                    <li key={line} className="flex gap-2">
                      <span className="mt-2.5 h-1 w-1 shrink-0 rounded-full bg-oracle-accent" />
                      <span>{line}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm leading-6 text-oracle-text">{c.generating}</p>
              )}
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
              <p className="text-[11px] uppercase tracking-wide text-oracle-accent">{c.priorities}</p>
              <p className="mt-2 text-lg font-semibold text-oracle-text">{c.thingsToCheck(inbox?.total ?? 0)}</p>
              <p className="mt-1 text-sm text-oracle-muted">{c.prioritiesBody}</p>
            </button>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => openAssetDetail()}
                className="rounded-2xl border border-oracle-border bg-oracle-bg/60 p-4 text-left transition-colors hover:bg-oracle-bg"
              >
                <Compass className="h-4 w-4 text-oracle-accent" />
                <p className="mt-2 text-sm font-semibold text-oracle-text">{c.asset}</p>
                <p className="mt-1 text-xs text-oracle-muted">{c.assetBody}</p>
              </button>
              <button
                onClick={() => setActiveSection("portfolio", "portfolio-theses")}
                className="rounded-2xl border border-oracle-border bg-oracle-bg/60 p-4 text-left transition-colors hover:bg-oracle-bg"
              >
                <BriefcaseBusiness className="h-4 w-4 text-oracle-accent" />
                <p className="mt-2 text-sm font-semibold text-oracle-text">{c.portfolio}</p>
                <p className="mt-1 text-xs text-oracle-muted">{c.portfolioBody}</p>
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setActiveSection("research")}
                className="rounded-2xl border border-oracle-border bg-oracle-bg/60 p-4 text-left transition-colors hover:bg-oracle-bg"
              >
                <Sparkles className="h-4 w-4 text-oracle-accent" />
                <p className="mt-2 text-sm font-semibold text-oracle-text">{c.research}</p>
                <p className="mt-1 text-xs text-oracle-muted">{c.researchBody}</p>
              </button>
              <button
                onClick={() => setActiveSection("assistant")}
                className="rounded-2xl border border-oracle-border bg-oracle-bg/60 p-4 text-left transition-colors hover:bg-oracle-bg"
              >
                <BellRing className="h-4 w-4 text-oracle-accent" />
                <p className="mt-2 text-sm font-semibold text-oracle-text">{c.assistant}</p>
                <p className="mt-1 text-xs text-oracle-muted">{c.assistantBody}</p>
              </button>
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-oracle-border bg-oracle-panel">
          <div className="border-b border-oracle-border px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">{c.top3}</p>
            <p className="mt-1 text-sm text-oracle-muted">{c.top3Body}</p>
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
                <p className="mt-1 text-xs leading-5 text-oracle-muted">{formatInlineDates(item.why_now || item.summary, language)}</p>
                <div className="mt-3 inline-flex items-center gap-1 text-xs text-oracle-accent">
                  {c.details}
                  <ArrowRight className="h-3.5 w-3.5" />
                </div>
              </button>
            ))}
            {topItems.length === 0 ? <p className="text-sm text-oracle-muted">{c.noPriorities}</p> : null}
          </div>
        </section>

        <section className="rounded-2xl border border-oracle-border bg-oracle-panel">
          <div className="border-b border-oracle-border px-4 py-3">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
              <CalendarClock className="h-3.5 w-3.5" />
              {c.events}
            </div>
            <p className="mt-1 text-sm text-oracle-muted">{c.eventsBody}</p>
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
            {nextEvents.length === 0 ? <p className="text-sm text-oracle-muted">{c.noEvents}</p> : null}
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
