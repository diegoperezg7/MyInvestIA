"use client";

import { useEffect, useState } from "react";
import useCurrencyStore from "@/stores/useCurrencyStore";

export default function CurrencyToggle({ collapsed = false }: { collapsed?: boolean }) {
  const { currency, toggleCurrency, rate, loading, hydrate } = useCurrencyStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    hydrate();
    setMounted(true);
  }, [hydrate]);

  if (!mounted) {
    return (
      <button className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md text-oracle-muted w-full">
        <span className="text-sm w-4 text-center">{"\u20AC"}</span>
        {!collapsed && <span>EUR</span>}
      </button>
    );
  }

  return (
    <button
      onClick={toggleCurrency}
      aria-label={currency === "USD" ? "Switch to EUR" : "Switch to USD"}
      className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md text-oracle-muted hover:text-oracle-text hover:bg-oracle-panel-hover transition-colors w-full"
    >
      <span className="text-sm w-4 text-center">
        {currency === "USD" ? "$" : "\u20AC"}
      </span>
      {!collapsed && (
        <span className="flex items-center gap-1.5">
          <span>{currency}</span>
          {!loading && rate !== 1 && (
            <span className="text-oracle-tertiary text-[10px]">
              1 USD = {rate.toFixed(4)} EUR
            </span>
          )}
          {loading && <span className="text-oracle-tertiary text-[10px]">...</span>}
        </span>
      )}
    </button>
  );
}
