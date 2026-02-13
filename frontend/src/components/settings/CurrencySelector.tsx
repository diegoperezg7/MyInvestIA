"use client";

import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";

export default function CurrencySelector() {
  const [currencies, setCurrencies] = useState<string[]>([]);
  const [selected, setSelected] = useState("USD");

  useEffect(() => {
    fetchAPI<{ currencies: string[] }>("/api/v1/market/currencies")
      .then((data) => setCurrencies(data.currencies))
      .catch(() => setCurrencies(["USD", "EUR", "GBP", "JPY"]));
  }, []);

  return (
    <select
      value={selected}
      onChange={(e) => setSelected(e.target.value)}
      className="bg-oracle-bg border border-oracle-border rounded px-2 py-1 text-xs text-oracle-text"
    >
      {currencies.map((c) => (
        <option key={c} value={c}>{c}</option>
      ))}
    </select>
  );
}
