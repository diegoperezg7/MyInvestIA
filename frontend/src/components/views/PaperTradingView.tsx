"use client";

import { useEffect, useState } from "react";
import { postAPI } from "@/lib/api";
import useCurrencyStore from "@/stores/useCurrencyStore";

interface PaperAccount {
  id: string;
  name: string;
  balance: number;
  initial_balance: number;
  total_value: number;
  total_pnl: number;
  total_pnl_percent: number;
  positions: PaperPosition[];
  created_at: string;
}

interface PaperPosition {
  symbol: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
}

interface PaperTrade {
  id: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  total: number;
  created_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function apiFetch<T>(endpoint: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${endpoint}`);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${resp.status}`);
  }
  return resp.json();
}

async function apiPost<T>(endpoint: string, body: unknown): Promise<T> {
  const resp = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || `API error: ${resp.status}`);
  }
  return resp.json();
}

export default function PaperTradingView() {
  const [account, setAccount] = useState<PaperAccount | null>(null);
  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { formatPrice } = useCurrencyStore();

  // Order form
  const [orderSymbol, setOrderSymbol] = useState("");
  const [orderSide, setOrderSide] = useState<"buy" | "sell">("buy");
  const [orderQty, setOrderQty] = useState("");
  const [orderResult, setOrderResult] = useState<string | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);

  const loadAccount = async (id: string) => {
    try {
      const data = await apiFetch<PaperAccount>(`/api/v1/paper/accounts/${id}`);
      setAccount(data);
      return data;
    } catch {
      return null;
    }
  };

  const loadTrades = async (id: string) => {
    try {
      const data = await apiFetch<{ trades: PaperTrade[] }>(`/api/v1/paper/accounts/${id}/trades`);
      setTrades(data.trades);
    } catch { /* ignore */ }
  };

  const createAccount = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiPost<PaperAccount>("/api/v1/paper/accounts", {
        name: "Main Paper Account",
        initial_balance: 100000,
      });
      setAccount(data);
      localStorage.setItem("paper_account_id", data.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create account");
    } finally {
      setLoading(false);
    }
  };

  const executeTrade = async () => {
    if (!account || !orderSymbol.trim() || !orderQty) return;
    setOrderResult(null);
    setOrderError(null);

    const qty = parseFloat(orderQty);
    if (isNaN(qty) || qty <= 0) {
      setOrderError("Enter a valid quantity");
      return;
    }

    try {
      await apiPost(`/api/v1/paper/accounts/${account.id}/trade`, {
        symbol: orderSymbol.trim().toUpperCase(),
        side: orderSide,
        quantity: qty,
      });
      setOrderResult(`${orderSide.toUpperCase()} ${qty} ${orderSymbol.toUpperCase()} executed`);
      setOrderSymbol("");
      setOrderQty("");
      loadAccount(account.id);
      loadTrades(account.id);
    } catch (e) {
      setOrderError(e instanceof Error ? e.message : "Trade failed");
    }
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      // Try saved account ID first, then "default"
      const savedId = localStorage.getItem("paper_account_id");
      const ids = savedId ? [savedId, "default"] : ["default"];

      for (const id of ids) {
        const data = await loadAccount(id);
        if (data) {
          localStorage.setItem("paper_account_id", data.id);
          await loadTrades(data.id);
          setLoading(false);
          return;
        }
      }

      // No account found — auto-create one
      await createAccount();
    };
    init();
  }, []);

  const pnlColor = (val: number) => (val >= 0 ? "text-oracle-green" : "text-oracle-red");

  if (loading && !account) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-12 text-center">
        <p className="text-oracle-muted text-sm">Loading paper trading account...</p>
      </div>
    );
  }

  if (!account) {
    return (
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-12 text-center">
        <p className="text-oracle-muted text-sm mb-4">
          Start with a virtual $100,000 portfolio to test your strategies risk-free.
        </p>
        <button
          onClick={createAccount}
          disabled={loading}
          className="bg-oracle-accent text-white px-6 py-2 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
        >
          {loading ? "Creating..." : "Create Paper Account"}
        </button>
        {error && <p className="text-oracle-red text-sm mt-3">{error}</p>}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Account summary */}
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
        <h3 className="text-oracle-muted text-xs font-medium uppercase tracking-wide mb-3">
          Account Summary
        </h3>
        <div className="space-y-3">
          <div>
            <p className="text-oracle-muted text-xs">Total Value</p>
            <p className="text-oracle-text text-2xl font-bold font-mono">
              {formatPrice(account.total_value)}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-oracle-muted text-xs">Cash Balance</p>
              <p className="text-oracle-text font-mono text-sm">
                {formatPrice(account.balance)}
              </p>
            </div>
            <div>
              <p className="text-oracle-muted text-xs">Total P&L</p>
              <p className={`font-mono text-sm ${pnlColor(account.total_pnl)}`}>
                {account.total_pnl >= 0 ? "+" : ""}{formatPrice(account.total_pnl)}
                <span className="text-xs ml-1">
                  ({account.total_pnl_percent >= 0 ? "+" : ""}{account.total_pnl_percent.toFixed(2)}%)
                </span>
              </p>
            </div>
          </div>
        </div>

        {/* Order form */}
        <div className="mt-4 pt-3 border-t border-oracle-border">
          <h4 className="text-oracle-muted text-xs font-medium uppercase mb-2">New Order</h4>
          <div className="space-y-2">
            <input
              type="text"
              value={orderSymbol}
              onChange={(e) => setOrderSymbol(e.target.value)}
              placeholder="Symbol (e.g. AAPL, BTC)"
              className="w-full bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
            />
            <div className="flex gap-2">
              <select
                value={orderSide}
                onChange={(e) => setOrderSide(e.target.value as "buy" | "sell")}
                className="bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
              >
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </select>
              <input
                type="number"
                value={orderQty}
                onChange={(e) => setOrderQty(e.target.value)}
                placeholder="Qty (e.g. 10)"
                min="0.001"
                step="any"
                className="flex-1 bg-oracle-bg border border-oracle-border rounded px-2 py-1.5 text-sm text-oracle-text"
              />
            </div>
            <button
              onClick={executeTrade}
              className={`w-full text-white text-sm py-2 rounded transition-colors ${
                orderSide === "buy"
                  ? "bg-oracle-green hover:bg-oracle-green/80"
                  : "bg-oracle-red hover:bg-oracle-red/80"
              }`}
            >
              {orderSide === "buy" ? "Buy" : "Sell"}
            </button>
            {orderResult && (
              <p className="text-xs text-oracle-green">{orderResult}</p>
            )}
            {orderError && (
              <p className="text-xs text-oracle-red">{orderError}</p>
            )}
          </div>
        </div>
      </div>

      {/* Positions */}
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
        <h3 className="text-oracle-muted text-xs font-medium uppercase tracking-wide mb-3">
          Positions ({account.positions.length})
        </h3>
        {account.positions.length === 0 && (
          <p className="text-oracle-muted text-sm">No open positions</p>
        )}
        <div className="space-y-2">
          {account.positions.map((pos) => (
            <div key={pos.symbol} className="bg-oracle-bg rounded p-2">
              <div className="flex items-center justify-between">
                <span className="text-oracle-text font-medium text-sm">{pos.symbol}</span>
                <span className={`text-xs font-mono ${pnlColor(pos.unrealized_pnl)}`}>
                  {pos.unrealized_pnl >= 0 ? "+" : ""}{formatPrice(pos.unrealized_pnl)}
                  <span className="text-oracle-muted ml-1">
                    ({pos.unrealized_pnl_percent >= 0 ? "+" : ""}{pos.unrealized_pnl_percent.toFixed(2)}%)
                  </span>
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-oracle-muted mt-1">
                <span>{pos.quantity} @ {formatPrice(pos.avg_price)}</span>
                <span>{formatPrice(pos.market_value)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Trade history */}
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
        <h3 className="text-oracle-muted text-xs font-medium uppercase tracking-wide mb-3">
          Trade History
        </h3>
        {trades.length === 0 && (
          <p className="text-oracle-muted text-sm">No trades yet</p>
        )}
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {trades.map((trade) => (
            <div key={trade.id} className="flex items-center justify-between text-sm py-1 border-b border-oracle-border/30">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-medium uppercase ${trade.side === "buy" ? "text-oracle-green" : "text-oracle-red"}`}>
                  {trade.side}
                </span>
                <span className="text-oracle-text">{trade.symbol}</span>
              </div>
              <div className="text-right text-oracle-muted text-xs">
                <span>{trade.quantity} @ {formatPrice(trade.price)}</span>
                <span className="ml-2 text-oracle-text">{formatPrice(trade.total)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
