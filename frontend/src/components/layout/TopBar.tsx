"use client";

import { Search, Sun, Moon, Home } from "lucide-react";
import { useView } from "@/contexts/ViewContext";
import { useTheme } from "@/contexts/ThemeContext";
import useLanguageStore from "@/stores/useLanguageStore";
import useCurrencyStore from "@/stores/useCurrencyStore";
import { useEffect, useState } from "react";

export default function TopBar() {
  const { setCommandBarOpen } = useView();
  const { theme, toggleTheme } = useTheme();
  const { language, toggleLanguage } = useLanguageStore();
  const { currency, toggleCurrency, rate, loading, hydrate } = useCurrencyStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    hydrate();
    setMounted(true);
  }, [hydrate]);

  return (
    <div className="hidden lg:flex items-center justify-end gap-2 h-12 px-6 border-b border-oracle-border shrink-0">
      {/* Search */}
      <button
        onClick={() => setCommandBarOpen(true)}
        className="flex items-center gap-2 px-3 py-1.5 text-sm text-oracle-muted hover:text-oracle-text bg-oracle-bg rounded-md hover:bg-oracle-panel-hover transition-colors border border-oracle-border"
      >
        <Search size={14} />
        <span>Buscar</span>
        <kbd className="text-[10px] bg-oracle-panel px-1.5 py-0.5 rounded ml-2">{"\u2318"}K</kbd>
      </button>

      <div className="w-px h-5 bg-oracle-border mx-1.5" />

      {/* Portal */}
      <button
        onClick={() => window.open("https://portal.darc3.com", "_self")}
        aria-label="Volver al Portal"
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-sm rounded-md text-oracle-muted hover:text-oracle-text hover:bg-oracle-panel-hover transition-colors"
        title="Volver al Portal"
      >
        <Home size={16} />
        <span>Portal</span>
      </button>

      {/* Theme */}
      <button
        onClick={toggleTheme}
        aria-label="Toggle theme"
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-sm rounded-md text-oracle-muted hover:text-oracle-text hover:bg-oracle-panel-hover transition-colors"
      >
        {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        <span>{theme === "dark" ? "Light" : "Dark"}</span>
      </button>

      {/* Language */}
      <button
        onClick={toggleLanguage}
        aria-label="Toggle language"
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-sm rounded-md text-oracle-muted hover:text-oracle-text hover:bg-oracle-panel-hover transition-colors"
      >
        <span className="font-medium">{language.toUpperCase()}</span>
        <span>{language === "es" ? "Español" : "English"}</span>
      </button>

      {/* Currency */}
      <button
        onClick={toggleCurrency}
        aria-label="Toggle currency"
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-sm rounded-md text-oracle-muted hover:text-oracle-text hover:bg-oracle-panel-hover transition-colors"
      >
        <span className="font-medium">{currency === "USD" ? "$" : "\u20AC"}</span>
        <span>{currency}</span>
        {mounted && !loading && rate !== 1 && (
          <span className="text-oracle-tertiary text-[10px]">
            1 USD = {rate.toFixed(4)} EUR
          </span>
        )}
      </button>
    </div>
  );
}
