"use client";

import { Compass, Home, Moon, Search, Sun } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useView } from "@/contexts/ViewContext";
import { getSectionDescription, getSectionLabel, getTabLabel } from "@/lib/shell";
import { useTheme } from "@/contexts/ThemeContext";
import useCurrencyStore from "@/stores/useCurrencyStore";
import useLanguageStore from "@/stores/useLanguageStore";

export default function TopBar() {
  const {
    activeSection,
    activeTab,
    commandBarOpen,
    focusView,
    selectedSymbol,
    setCommandBarOpen,
  } = useView();
  const { theme, toggleTheme } = useTheme();
  const { language, toggleLanguage } = useLanguageStore();
  const { currency, toggleCurrency, rate, loading, hydrate } = useCurrencyStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    hydrate();
    setMounted(true);
  }, [hydrate]);

  const shellCopy = useMemo(() => {
    if (focusView === "asset-detail") {
      return {
        label: language === "es" ? "Detalle del activo" : "Asset detail",
        description:
          selectedSymbol && language === "es"
            ? `Contexto completo para ${selectedSymbol}`
            : selectedSymbol && language === "en"
              ? `Full context for ${selectedSymbol}`
              : language === "es"
                ? "Precio, noticias, sentimiento, filings y contexto"
                : "Price, news, sentiment, filings and context",
        eyebrow: selectedSymbol || (language === "es" ? "Símbolo" : "Symbol"),
      };
    }

    return {
      label: getSectionLabel(activeSection, language),
      description: getSectionDescription(activeSection, language),
      eyebrow: getTabLabel(activeTab, language),
    };
  }, [activeSection, activeTab, focusView, language, selectedSymbol]);

  return (
    <div className="hidden h-14 items-center justify-between gap-4 border-b border-oracle-border px-6 shrink-0 lg:flex">
      <div className="min-w-0">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
          {focusView === "asset-detail" ? <Compass className="h-3.5 w-3.5" /> : null}
          <span>{shellCopy.eyebrow}</span>
        </div>
        <div className="mt-1 flex items-baseline gap-3">
          <h1 className="truncate text-lg font-semibold text-oracle-text">{shellCopy.label}</h1>
          <p className="truncate text-sm text-oracle-muted">{shellCopy.description}</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => setCommandBarOpen(!commandBarOpen)}
          className="flex items-center gap-2 rounded-md border border-oracle-border bg-oracle-bg px-3 py-1.5 text-sm text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
        >
          <Search size={14} />
          <span>{language === "es" ? "Buscar" : "Search"}</span>
          <kbd className="ml-2 rounded bg-oracle-panel px-1.5 py-0.5 text-[10px]">
            {"\u2318"}K
          </kbd>
        </button>

        <div className="mx-1.5 h-5 w-px bg-oracle-border" />

        <button
          onClick={() => window.open(process.env.NEXT_PUBLIC_PORTAL_URL || "/", "_self")}
          aria-label={language === "es" ? "Volver al Portal" : "Back to Portal"}
          className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
          title={language === "es" ? "Volver al Portal" : "Back to Portal"}
        >
          <Home size={16} />
          <span>Portal</span>
        </button>

        <button
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          <span>{theme === "dark" ? "Light" : "Dark"}</span>
        </button>

        <button
          onClick={toggleLanguage}
          aria-label="Toggle language"
          className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
        >
          <span className="font-medium">{language.toUpperCase()}</span>
          <span>{language === "es" ? "Español" : "English"}</span>
        </button>

        <button
          onClick={toggleCurrency}
          aria-label="Toggle currency"
          className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
        >
          <span className="font-medium">{currency === "USD" ? "$" : "\u20AC"}</span>
          <span>{currency}</span>
          {mounted && !loading && rate !== 1 ? (
            <span className="text-[10px] text-oracle-tertiary">
              1 USD = {rate.toFixed(4)} EUR
            </span>
          ) : null}
        </button>
      </div>
    </div>
  );
}
