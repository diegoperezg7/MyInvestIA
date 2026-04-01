import type {
  LegacyViewAlias,
  SectionId,
  SectionTabId,
} from "@/types";

export interface LocalizedCopy {
  es: string;
  en: string;
}

export interface SectionCopy {
  label: LocalizedCopy;
  description: LocalizedCopy;
}

export interface SectionTabCopy {
  id: SectionTabId;
  section: SectionId;
  label: LocalizedCopy;
  description?: LocalizedCopy;
}

export const SECTION_ORDER: SectionId[] = [
  "home",
  "priorities",
  "portfolio",
  "research",
  "markets",
  "assistant",
  "settings",
];

export const SECTION_COPY: Record<SectionId, SectionCopy> = {
  home: {
    label: { es: "Inicio", en: "Home" },
    description: {
      es: "Tu punto de partida: prioridades, cartera y contexto.",
      en: "Your starting point: priorities, portfolio and context.",
    },
  },
  priorities: {
    label: { es: "Prioridades", en: "Priorities" },
    description: {
      es: "Lo que merece atención ahora mismo.",
      en: "What deserves attention right now.",
    },
  },
  portfolio: {
    label: { es: "Cartera", en: "Portfolio" },
    description: {
      es: "Posiciones, watchlists, tesis y alertas ligadas a tus activos.",
      en: "Positions, watchlists, theses and alerts tied to your assets.",
    },
  },
  research: {
    label: { es: "Investigación", en: "Research" },
    description: {
      es: "Ideas, buscador, factores y señal IA.",
      en: "Ideas, screener, factors and AI signal.",
    },
  },
  markets: {
    label: { es: "Mercados", en: "Markets" },
    description: {
      es: "Pulso del día, macro, calendario y movimientos.",
      en: "Daily pulse, macro, calendar and moves.",
    },
  },
  assistant: {
    label: { es: "Asistente", en: "Assistant" },
    description: {
      es: "Chat, bot Telegram, alertas, conexiones y laboratorio.",
      en: "Chat, Telegram bot, alerts, connections and lab.",
    },
  },
  settings: {
    label: { es: "Ajustes", en: "Settings" },
    description: {
      es: "Configuración de tu cuenta y de la app.",
      en: "Account and app settings.",
    },
  },
};

export const DEFAULT_TAB_BY_SECTION: Record<SectionId, SectionTabId> = {
  home: "home-summary",
  priorities: "priorities-inbox",
  portfolio: "portfolio-overview",
  research: "research-ideas",
  markets: "markets-today",
  assistant: "assistant-chat",
  settings: "settings-general",
};

export const SECTION_TABS: Record<SectionId, SectionTabCopy[]> = {
  home: [
    {
      id: "home-summary",
      section: "home",
      label: { es: "Resumen", en: "Summary" },
      description: {
        es: "Qué pasa hoy y por dónde empezar.",
        en: "What is happening today and where to start.",
      },
    },
  ],
  priorities: [
    {
      id: "priorities-inbox",
      section: "priorities",
      label: { es: "Bandeja", en: "Inbox" },
      description: {
        es: "Riesgos, oportunidades y siguientes pasos.",
        en: "Risks, opportunities and next steps.",
      },
    },
  ],
  portfolio: [
    {
      id: "portfolio-overview",
      section: "portfolio",
      label: { es: "Cartera y riesgo", en: "Portfolio & risk" },
      description: {
        es: "Posiciones, P&L y exposición.",
        en: "Positions, P&L and exposure.",
      },
    },
    {
      id: "portfolio-watchlists",
      section: "portfolio",
      label: { es: "Watchlists", en: "Watchlists" },
      description: {
        es: "Activos que sigues de cerca.",
        en: "Assets you are following closely.",
      },
    },
    {
      id: "portfolio-theses",
      section: "portfolio",
      label: { es: "Tesis", en: "Theses" },
      description: {
        es: "Ideas vivas y revisiones.",
        en: "Live ideas and reviews.",
      },
    },
    {
      id: "portfolio-alerts",
      section: "portfolio",
      label: { es: "Alertas", en: "Alerts" },
      description: {
        es: "Señales y avisos para tus activos.",
        en: "Signals and alerts for your assets.",
      },
    },
  ],
  research: [
    {
      id: "research-ideas",
      section: "research",
      label: { es: "Ideas", en: "Ideas" },
      description: {
        es: "Ranking y validación ligera.",
        en: "Ranking and light validation.",
      },
    },
    {
      id: "research-screener",
      section: "research",
      label: { es: "Buscador", en: "Screener" },
      description: {
        es: "Filtra oportunidades con reglas simples.",
        en: "Filter opportunities with simple rules.",
      },
    },
    {
      id: "research-factors",
      section: "research",
      label: { es: "Factores", en: "Factors" },
      description: {
        es: "Qué apoya o frena una idea.",
        en: "What supports or weakens an idea.",
      },
    },
    {
      id: "research-signal",
      section: "research",
      label: { es: "Señal IA", en: "AI Signal" },
      description: {
        es: "Resumen sintético para un símbolo.",
        en: "Synthetic summary for a symbol.",
      },
    },
  ],
  markets: [
    {
      id: "markets-today",
      section: "markets",
      label: { es: "Hoy", en: "Today" },
      description: {
        es: "Pulso general del mercado.",
        en: "General market pulse.",
      },
    },
    {
      id: "markets-macro",
      section: "markets",
      label: { es: "Macro", en: "Macro" },
      description: {
        es: "Indicadores y contexto oficial.",
        en: "Official indicators and context.",
      },
    },
    {
      id: "markets-calendar",
      section: "markets",
      label: { es: "Calendario", en: "Calendar" },
      description: {
        es: "Próximos catalizadores.",
        en: "Upcoming catalysts.",
      },
    },
    {
      id: "markets-moves",
      section: "markets",
      label: { es: "Movimientos", en: "Moves" },
      description: {
        es: "Ganadores, perdedores y volatilidad.",
        en: "Gainers, losers and volatility.",
      },
    },
    {
      id: "markets-maps",
      section: "markets",
      label: { es: "Mapas y materias primas", en: "Maps & commodities" },
      description: {
        es: "Sectores y materias primas de un vistazo.",
        en: "Sectors and commodities at a glance.",
      },
    },
  ],
  assistant: [
    {
      id: "assistant-chat",
      section: "assistant",
      label: { es: "Chat", en: "Chat" },
      description: {
        es: "Respuestas y explicaciones.",
        en: "Answers and explanations.",
      },
    },
    {
      id: "assistant-bot",
      section: "assistant",
      label: { es: "Bot Telegram", en: "Telegram bot" },
      description: {
        es: "Avisos automáticos para tu cuenta.",
        en: "Automatic alerts for your account.",
      },
    },
    {
      id: "assistant-alerts",
      section: "assistant",
      label: { es: "Alertas", en: "Alerts" },
      description: {
        es: "Escaneo y reglas accionables.",
        en: "Scan and actionable rules.",
      },
    },
    {
      id: "assistant-connections",
      section: "assistant",
      label: { es: "Conexiones", en: "Connections" },
      description: {
        es: "Exchanges, wallets y brokers.",
        en: "Exchanges, wallets and brokers.",
      },
    },
    {
      id: "assistant-lab",
      section: "assistant",
      label: { es: "Laboratorio", en: "Lab" },
      description: {
        es: "Herramientas avanzadas y beta.",
        en: "Advanced and beta tools.",
      },
    },
  ],
  settings: [
    {
      id: "settings-general",
      section: "settings",
      label: { es: "General", en: "General" },
      description: {
        es: "Cuenta, preferencias y automatización.",
        en: "Account, preferences and automation.",
      },
    },
  ],
};

export const LEGACY_VIEW_TO_SHELL: Record<
  LegacyViewAlias,
  {
    section: SectionId;
    tab: SectionTabId;
    focus?: "asset-detail";
  }
> = {
  overview: { section: "home", tab: "home-summary" },
  inbox: { section: "priorities", tab: "priorities-inbox" },
  recommendations: { section: "priorities", tab: "priorities-inbox" },
  terminal: {
    section: "research",
    tab: "research-ideas",
    focus: "asset-detail",
  },
  analysis: { section: "research", tab: "research-factors" },
  screener: { section: "research", tab: "research-screener" },
  prediction: { section: "research", tab: "research-signal" },
  research: { section: "research", tab: "research-ideas" },
  theses: { section: "portfolio", tab: "portfolio-theses" },
  movers: { section: "markets", tab: "markets-moves" },
  volatility: { section: "markets", tab: "markets-moves" },
  commodities: { section: "markets", tab: "markets-maps" },
  heatmap: { section: "markets", tab: "markets-maps" },
  macro: { section: "markets", tab: "markets-macro" },
  calendar: { section: "markets", tab: "markets-calendar" },
  chat: { section: "assistant", tab: "assistant-chat" },
  alerts: { section: "assistant", tab: "assistant-alerts" },
  connections: { section: "assistant", tab: "assistant-connections" },
  "paper-trade": { section: "assistant", tab: "assistant-lab" },
  "rl-trading": { section: "assistant", tab: "assistant-lab" },
  settings: { section: "settings", tab: "settings-general" },
};

export function isTabForSection(
  section: SectionId,
  tab: SectionTabId | null | undefined,
): tab is SectionTabId {
  if (!tab) return false;
  return SECTION_TABS[section].some((item) => item.id === tab);
}

export function getDefaultTab(section: SectionId): SectionTabId {
  return DEFAULT_TAB_BY_SECTION[section];
}

export function getSectionLabel(section: SectionId, language: "es" | "en") {
  return SECTION_COPY[section].label[language];
}

export function getSectionDescription(section: SectionId, language: "es" | "en") {
  return SECTION_COPY[section].description[language];
}

export function getTabLabel(tab: SectionTabId, language: "es" | "en") {
  const tabCopy = Object.values(SECTION_TABS)
    .flat()
    .find((item) => item.id === tab);
  if (!tabCopy) return tab;
  return tabCopy.label[language];
}

export function getStoredShellState() {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem("myinvestia-shell");
    if (!raw) return null;
    const parsed = JSON.parse(raw) as {
      section?: SectionId;
      tab?: SectionTabId;
    };
    if (!parsed.section || !(parsed.section in DEFAULT_TAB_BY_SECTION)) {
      return null;
    }
    return {
      section: parsed.section,
      tab: isTabForSection(parsed.section, parsed.tab)
        ? parsed.tab
        : getDefaultTab(parsed.section),
    };
  } catch {
    return null;
  }
}
