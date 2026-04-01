"use client";

import { Compass, Menu, Moon, Settings, Sun } from "lucide-react";

import { useView } from "@/contexts/ViewContext";
import { useTheme } from "@/contexts/ThemeContext";
import { getSectionLabel, getTabLabel } from "@/lib/shell";
import useCurrencyStore from "@/stores/useCurrencyStore";
import useLanguageStore from "@/stores/useLanguageStore";

export default function MobileTopBar() {
  const {
    activeSection,
    activeTab,
    focusView,
    selectedSymbol,
    setActiveView,
    setSidebarMobileOpen,
  } = useView();
  const { theme, toggleTheme } = useTheme();
  const { language, toggleLanguage } = useLanguageStore();
  const { currency, toggleCurrency } = useCurrencyStore();

  const title =
    focusView === "asset-detail"
      ? language === "es"
        ? "Detalle del activo"
        : "Asset detail"
      : getSectionLabel(activeSection, language);
  const subtitle =
    focusView === "asset-detail"
      ? selectedSymbol || (language === "es" ? "Símbolo" : "Symbol")
      : getTabLabel(activeTab, language);

  return (
    <div className="flex h-14 items-center justify-between gap-2 border-b border-oracle-border bg-oracle-panel px-3 lg:hidden">
      <div className="flex min-w-0 items-center gap-2">
        <button
          onClick={() => setSidebarMobileOpen(true)}
          className="rounded-md p-1.5 text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        <div className="min-w-0">
          <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
            {focusView === "asset-detail" ? <Compass className="h-3 w-3" /> : null}
            <span className="truncate">{subtitle}</span>
          </div>
          <p className="truncate text-sm font-semibold text-oracle-text">{title}</p>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={() => setActiveView("settings")}
          className="rounded-md p-1.5 text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
          aria-label="Settings"
        >
          <Settings size={18} />
        </button>
        <button
          onClick={toggleTheme}
          className="rounded-md p-1.5 text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button
          onClick={toggleLanguage}
          className="rounded-md px-1.5 py-1 text-xs font-semibold text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
          aria-label="Toggle language"
        >
          {language.toUpperCase()}
        </button>
        <button
          onClick={toggleCurrency}
          className="rounded-md px-1.5 py-1 text-xs font-semibold text-oracle-muted transition-colors hover:bg-oracle-panel-hover hover:text-oracle-text"
          aria-label="Toggle currency"
        >
          {currency === "USD" ? "$" : "€"}
        </button>
      </div>
    </div>
  );
}
