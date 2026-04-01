import type {
  ImpactLevel,
  InboxItem,
  InboxScope,
  InboxStatus,
  InsightState,
  ThesisLifecycleStatus,
  ThesisReviewState,
  ThesisStance,
} from "@/types";

function mapValue<T extends string>(
  value: T,
  labels: Record<T, { es: string; en: string }>,
  language: "es" | "en",
) {
  return labels[value]?.[language] ?? value;
}

export function getInboxStateLabel(
  state: InsightState,
  language: "es" | "en" = "es",
) {
  return mapValue(
    state,
    {
      confirmed: {
        es: "Confirmado",
        en: "Confirmed",
      },
      exploratory: {
        es: "Por confirmar",
        en: "Needs confirmation",
      },
    },
    language,
  );
}

export function getInboxScopeLabel(
  scope: InboxScope,
  language: "es" | "en" = "es",
) {
  return mapValue(
    scope,
    {
      portfolio: { es: "Mi cartera", en: "Portfolio" },
      watchlist: { es: "Seguimiento", en: "Watchlist" },
      macro: { es: "Macro", en: "Macro" },
      research: { es: "Investigación", en: "Research" },
    },
    language,
  );
}

export function getInboxStatusLabel(
  status: InboxStatus,
  language: "es" | "en" = "es",
) {
  return mapValue(
    status,
    {
      open: { es: "Activo", en: "Open" },
      saved: { es: "Guardado", en: "Saved" },
      dismissed: { es: "Descartado", en: "Dismissed" },
      snoozed: { es: "Pospuesto", en: "Snoozed" },
      done: { es: "Hecho", en: "Done" },
    },
    language,
  );
}

export function getImpactLabel(
  impact: ImpactLevel,
  language: "es" | "en" = "es",
) {
  return mapValue(
    impact,
    {
      low: { es: "Bajo", en: "Low" },
      medium: { es: "Medio", en: "Medium" },
      high: { es: "Alto", en: "High" },
    },
    language,
  );
}

export function getHorizonLabel(
  horizon: InboxItem["horizon"],
  language: "es" | "en" = "es",
) {
  return mapValue(
    horizon,
    {
      immediate: { es: "Ahora", en: "Now" },
      short: { es: "Corto plazo", en: "Short term" },
      medium: { es: "Medio plazo", en: "Medium term" },
      long: { es: "Largo plazo", en: "Long term" },
    },
    language,
  );
}

export function getAssistantModeLabel(
  mode: InboxItem["assistant_mode"],
  language: "es" | "en" = "es",
) {
  return mapValue(
    mode,
    {
      prudent: { es: "Prudente", en: "Prudent" },
      balanced: { es: "Equilibrado", en: "Balanced" },
      proactive: { es: "Activo", en: "Proactive" },
    },
    language,
  );
}

export function getInboxKindLabel(
  kind: string,
  language: "es" | "en" = "es",
) {
  const normalized = kind.toLowerCase();
  const known: Record<string, { es: string; en: string }> = {
    risk: { es: "Riesgo", en: "Risk" },
    opportunity: { es: "Oportunidad", en: "Opportunity" },
    event: { es: "Evento", en: "Event" },
    catalyst: { es: "Catalizador", en: "Catalyst" },
    thesis: { es: "Tesis", en: "Thesis" },
    sentiment: { es: "Señal de sentimiento", en: "Sentiment signal" },
    macro: { es: "Macro", en: "Macro" },
    alert: { es: "Alerta", en: "Alert" },
    filing: { es: "Filing", en: "Filing" },
    insider: { es: "Movimiento interno", en: "Insider activity" },
    research: { es: "Investigación", en: "Research" },
  };

  if (known[normalized]) {
    return known[normalized][language];
  }

  const humanized = normalized.replace(/[_-]+/g, " ");
  if (language === "es") {
    return humanized
      .replace("social", "redes")
      .replace("news", "noticias")
      .replace("price", "precio")
      .replace("volume", "volumen");
  }
  return humanized;
}

export function getThesisStanceLabel(
  stance: ThesisStance,
  language: "es" | "en" = "es",
) {
  return mapValue(
    stance,
    {
      bull: { es: "Alcista", en: "Bullish" },
      base: { es: "Base", en: "Base" },
      bear: { es: "Bajista", en: "Bearish" },
    },
    language,
  );
}

export function getThesisStatusLabel(
  status: ThesisLifecycleStatus,
  language: "es" | "en" = "es",
) {
  return mapValue(
    status,
    {
      active: { es: "Activa", en: "Active" },
      paused: { es: "Pausada", en: "Paused" },
      closed: { es: "Cerrada", en: "Closed" },
    },
    language,
  );
}

export function getThesisReviewStateLabel(
  reviewState: ThesisReviewState,
  language: "es" | "en" = "es",
) {
  return mapValue(
    reviewState,
    {
      validating: { es: "Validando", en: "Validating" },
      at_risk: { es: "En riesgo", en: "At risk" },
      broken: { es: "Rota", en: "Broken" },
    },
    language,
  );
}

export function getConfidenceBand(
  value: number,
  language: "es" | "en" = "es",
) {
  if (value >= 0.75) return language === "es" ? "Alta" : "High";
  if (value >= 0.45) return language === "es" ? "Media" : "Medium";
  return language === "es" ? "Baja" : "Low";
}
