"use client";

import { Menu, Sun, Moon } from "lucide-react";
import { useView } from "@/contexts/ViewContext";
import { useTheme } from "@/contexts/ThemeContext";
import useLanguageStore from "@/stores/useLanguageStore";
import useCurrencyStore from "@/stores/useCurrencyStore";

export default function MobileTopBar() {
  const { setSidebarMobileOpen } = useView();
  const { theme, toggleTheme } = useTheme();
  const { language, toggleLanguage } = useLanguageStore();
  const { currency, toggleCurrency } = useCurrencyStore();

  return (
    <div className="flex items-center justify-between h-12 px-3 border-b border-oracle-border bg-oracle-panel lg:hidden">
      <div className="flex items-center gap-2">
        <button
          onClick={() => setSidebarMobileOpen(true)}
          className="text-oracle-muted hover:text-oracle-text p-1.5"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        <span
          className="font-bold text-sm tracking-wider"
          style={{ color: "var(--oracle-primary)" }}
        >
          MyInvest<span className="text-oracle-text">IA</span>
        </span>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={toggleTheme}
          className="text-oracle-muted hover:text-oracle-text p-1.5 rounded-md active:bg-oracle-panel-hover"
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        <button
          onClick={toggleLanguage}
          className="text-oracle-muted hover:text-oracle-text px-1.5 py-1 rounded-md text-xs font-semibold active:bg-oracle-panel-hover"
          aria-label="Toggle language"
        >
          {language.toUpperCase()}
        </button>

        <button
          onClick={toggleCurrency}
          className="text-oracle-muted hover:text-oracle-text px-1.5 py-1 rounded-md text-xs font-semibold active:bg-oracle-panel-hover"
          aria-label="Toggle currency"
        >
          {currency === "USD" ? "$" : "€"}{currency}
        </button>
      </div>
    </div>
  );
}
