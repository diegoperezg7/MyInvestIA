"use client";

import { useState } from "react";
import { postAPI } from "@/lib/api";

interface Props {
  onSuccess: () => void;
}

export default function TransactionForm({ onSuccess }: Props) {
  const [symbol, setSymbol] = useState("");
  const [type, setType] = useState<"buy" | "sell" | "dividend">("buy");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!symbol.trim() || !quantity || !price) return;
    setError(null);

    try {
      await postAPI("/api/v1/transactions/", {
        symbol: symbol.trim().toUpperCase(),
        type,
        quantity: parseFloat(quantity),
        price: parseFloat(price),
      });
      setSymbol("");
      setQuantity("");
      setPrice("");
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create transaction");
    }
  };

  return (
    <div className="bg-oracle-bg rounded p-3 mb-3">
      <div className="grid grid-cols-2 gap-2 mb-2">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Symbol"
          className="bg-oracle-panel border border-oracle-border rounded px-2 py-1 text-sm text-oracle-text"
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value as typeof type)}
          className="bg-oracle-panel border border-oracle-border rounded px-2 py-1 text-sm text-oracle-text"
        >
          <option value="buy">Buy</option>
          <option value="sell">Sell</option>
          <option value="dividend">Dividend</option>
        </select>
      </div>
      <div className="grid grid-cols-2 gap-2 mb-2">
        <input
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="Quantity"
          className="bg-oracle-panel border border-oracle-border rounded px-2 py-1 text-sm text-oracle-text"
        />
        <input
          type="number"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          placeholder="Price"
          className="bg-oracle-panel border border-oracle-border rounded px-2 py-1 text-sm text-oracle-text"
        />
      </div>
      {error && <p className="text-oracle-red text-xs mb-2">{error}</p>}
      <button
        onClick={handleSubmit}
        className="w-full bg-oracle-accent text-white text-sm py-1.5 rounded hover:bg-oracle-accent/80 transition-colors"
      >
        Record Transaction
      </button>
    </div>
  );
}
