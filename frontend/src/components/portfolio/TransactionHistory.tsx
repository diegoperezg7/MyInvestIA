"use client";

import { useEffect, useState } from "react";
import { fetchAPI, deleteAPI } from "@/lib/api";
import useCurrencyStore from "@/stores/useCurrencyStore";
import TransactionForm from "./TransactionForm";

interface Transaction {
  id: string;
  symbol: string;
  type: "buy" | "sell" | "dividend";
  quantity: number;
  price: number;
  total: number;
  date: string;
  notes: string;
}

const TYPE_COLORS: Record<string, string> = {
  buy: "text-oracle-green",
  sell: "text-oracle-red",
  dividend: "text-oracle-accent",
};

export default function TransactionHistory() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const { formatPrice } = useCurrencyStore();

  const loadTransactions = async () => {
    try {
      const data = await fetchAPI<{ transactions: Transaction[] }>("/api/v1/transactions/");
      setTransactions(data.transactions);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => {
    loadTransactions();
  }, []);

  const handleDelete = async (id: string) => {
    await deleteAPI(`/api/v1/transactions/${id}`);
    loadTransactions();
  };

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-oracle-muted text-xs font-medium uppercase tracking-wide">
          Transactions
        </h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-xs text-oracle-accent hover:text-oracle-accent/80"
        >
          {showForm ? "Cancel" : "+ Add"}
        </button>
      </div>

      {showForm && (
        <TransactionForm onSuccess={() => { loadTransactions(); setShowForm(false); }} />
      )}

      {loading && <p className="text-oracle-muted text-sm">Loading...</p>}

      {transactions.length === 0 && !loading && (
        <p className="text-oracle-muted text-sm">No transactions recorded yet.</p>
      )}

      <div className="space-y-1 max-h-64 overflow-y-auto">
        {transactions.map((txn) => (
          <div key={txn.id} className="flex items-center justify-between text-sm py-1.5 border-b border-oracle-border/30">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-medium uppercase ${TYPE_COLORS[txn.type]}`}>
                {txn.type}
              </span>
              <span className="text-oracle-text">{txn.symbol}</span>
              <span className="text-oracle-muted text-xs">
                {txn.quantity} @ {formatPrice(txn.price)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-oracle-text text-xs font-mono">{formatPrice(txn.total)}</span>
              <button
                onClick={() => handleDelete(txn.id)}
                className="text-oracle-muted hover:text-oracle-red text-xs"
              >
                x
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
