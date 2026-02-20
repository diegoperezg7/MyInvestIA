"use client";

import { useState, useEffect, useCallback } from "react";
import { getToken } from "@/lib/auth";
import SparklineChart from "@/components/charts/SparklineChart";

interface AgentStatus {
  model_loaded: boolean;
  mode: string;
  symbol: string;
  position: number;
  entry_price: number;
  current_price: number;
  max_position_pct: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  total_trades: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

interface Performance {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  initial_balance: number;
  current_estimate: number;
  daily_pnl: number;
  weekly_pnl: number;
  monthly_pnl: number;
  equity_curve: number[];
  best_trade: number;
  worst_trade: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  sharpe_ratio: number;
  max_drawdown: number;
}

interface Trade {
  id: string;
  symbol: string;
  action: string;
  price: number;
  quantity: number;
  value: number;
  pnl: number;
  confidence: number;
  reason: string;
  timestamp: string;
}

interface Signal {
  action: string;
  confidence: number;
  reason: string;
  momentum: number;
  rsi: number;
  volume_ratio: number;
  entry_price?: number;
  current_price?: number;
}

interface SignalResponse {
  signal: Signal;
  current_price?: number;
  executed?: boolean;
  trade?: Trade;
}

export default function RLTradingView() {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [performance, setPerformance] = useState<Performance | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [signal, setSignal] = useState<Signal | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [autoTrade, setAutoTrade] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [signalKey, setSignalKey] = useState(0);

  const api = useCallback(async (endpoint: string, options?: RequestInit) => {
    const token = getToken();
    const res = await fetch(`/api/v1${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options?.headers,
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Error" }));
      throw new Error(err.detail || "Error de API");
    }
    return res.json();
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await api("/rl-agent/status");
      if (data && data.symbol) {
        setStatus(data);
        setIsInitialized(true);
      } else {
        setIsInitialized(false);
      }
    } catch (e) {
      console.error("Error fetching status:", e);
      setIsInitialized(false);
    }
  }, [api]);

  const fetchPerformance = useCallback(async () => {
    try {
      const data = await api("/rl-agent/performance");
      setPerformance(data);
    } catch (e) {
      console.error("Error fetching performance:", e);
    }
  }, [api]);

  const fetchTrades = useCallback(async () => {
    try {
      const data = await api("/rl-agent/trades?limit=50");
      const tradesData = Array.isArray(data) ? data : (data?.trades || []);
      setTrades(tradesData);
    } catch (e) {
      console.error("Error fetching trades:", e);
      setTrades([]); // Always set to array on error
    }
  }, [api]);

  const fetchSignal = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      console.log("Fetching signal...");
      const data: SignalResponse = await api("/rl-agent/signal", {
        method: "POST",
        body: JSON.stringify({
          data: [],
          current_price: 45000,
          _t: Date.now(),
        }),
      });
      console.log("Signal response:", data);
      const signalData = data.signal || data;
      console.log("Setting signal:", signalData);
      setSignal({...signalData});
      setLastUpdate(new Date());
      setSignalKey(k => k + 1);
      // Use current_price from response, or fallback to signal's current_price
      const price = data.current_price || signalData.current_price;
      if (price) {
        console.log("Setting price:", price);
        setCurrentPrice(price);
      }
      console.log("Signal set:", signalData);
      
      // Auto-trade: ejecutar automáticamente si hay señal clara
      if (autoTrade && signalData.action !== "hold" && signalData.confidence >= 0.4) {
        console.log("Auto-trade enabled, executing trade for:", signalData.action);
        try {
          const result: SignalResponse = await api("/rl-agent/trade", {
            method: "POST",
            body: JSON.stringify({
              data: [],
              current_price: data.current_price || 45000,
            }),
          });
          console.log("Auto-trade result:", result);
          
          if (result.executed) {
            setError(null);
            await fetchStatus();
            await fetchPerformance();
            await fetchTrades();
          }
        } catch (tradeError: any) {
          console.error("Auto-trade error:", tradeError);
        }
      }
    } catch (e: any) {
      console.error("Error fetching signal:", e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [api, autoTrade, fetchStatus, fetchPerformance, fetchTrades]);

  const initAgent = async (mode: string) => {
    setLoading(true);
    setError(null);
    try {
      await api("/rl-agent/init", {
        method: "POST",
        body: JSON.stringify({
          symbol: "BTC/USD",
          mode,
          initial_balance: 10000,
          max_position_pct: 0.1,
          stop_loss_pct: 0.05,
          take_profit_pct: 0.1,
        }),
      });
      await fetchStatus();
      await fetchPerformance();
      await fetchTrades();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const updateMode = async (mode: string) => {
    setLoading(true);
    try {
      await api("/rl-agent/mode", {
        method: "POST",
        body: JSON.stringify({ mode }),
      });
      await fetchStatus();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const closePosition = async () => {
    if (!status?.entry_price) return;
    setLoading(true);
    try {
      await api("/rl-agent/close-position", {
        method: "POST",
        body: JSON.stringify({ current_price: status.entry_price * 1.01 }),
      });
      await fetchStatus();
      await fetchPerformance();
      await fetchTrades();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const executeTrade = async () => {
    setLoading(true);
    setError(null);
    try {
      const price = currentPrice || signal?.current_price || 45000;
      console.log("Executing trade with price:", price);
      const result: SignalResponse = await api("/rl-agent/trade", {
        method: "POST",
        body: JSON.stringify({
          data: [],
          current_price: price,
        }),
      });
      console.log("Trade result:", result);
      
      if (result.executed) {
        setError(null);
        await fetchStatus();
        await fetchPerformance();
        await fetchTrades();
      } else if (result.signal?.reason) {
        setError(result.signal.reason);
      }
    } catch (e: any) {
      console.error("Trade error:", e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchPerformance();
    fetchTrades();

    const interval = setInterval(() => {
      if (isInitialized && autoTrade) {
        fetchSignal();
      }
      fetchStatus();
      fetchPerformance();
    }, 300000); // 5 minutes

    return () => clearInterval(interval);
  }, [isInitialized, autoTrade, fetchSignal, fetchStatus, fetchPerformance]);

  const fmtNum = (n: number | undefined | null, decimals = 2) => {
    if (n === undefined || n === null) return "-";
    return n.toFixed(decimals);
  };

  const fmtMoney = (n: number | undefined | null) => {
    if (n === undefined || n === null) return "-";
    const prefix = n >= 0 ? "+" : "";
    return `${prefix}$${Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const fmtPct = (n: number | undefined | null) => {
    if (n === undefined || n === null) return "-";
    const prefix = n >= 0 ? "+" : "";
    return `${prefix}${n.toFixed(2)}%`;
  };

  const getModeLabel = (mode: string) => {
    switch (mode) {
      case "paper": return "PAPEL";
      case "shadow": return "SOMBRA";
      case "live": return "REAL";
      default: return mode?.toUpperCase() || "PAPEL";
    }
  };

  const getModeColor = (mode: string) => {
    switch (mode) {
      case "paper": return "bg-oracle-green";
      case "shadow": return "bg-yellow-500";
      case "live": return "bg-oracle-red";
      default: return "bg-oracle-accent";
    }
  };

  const getPositionLabel = (pos: number) => {
    switch (pos) {
      case 1: return "LARGO";
      case -1: return "CORTO";
      default: return "FLAT";
    }
  };

  const getPositionColor = (pos: number) => {
    switch (pos) {
      case 1: return "text-oracle-green";
      case -1: return "text-oracle-red";
      default: return "text-oracle-muted";
    }
  };

  const getPnlColor = (val: number) => {
    return val >= 0 ? "text-oracle-green" : "text-oracle-red";
  };

  if (!isInitialized) {
    return (
      <div className="space-y-4">
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-oracle-accent/20 flex items-center justify-center">
            <svg className="w-8 h-8 text-oracle-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h2 className="text-oracle-text text-2xl font-bold mb-2">
            Agente de Trading RL
          </h2>
          <p className="text-oracle-muted text-sm mb-6 max-w-md mx-auto">
            Inicializa el agente de aprendizaje por refuerzo para comenzar a operar con inteligencia artificial
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <button
              onClick={() => initAgent("paper")}
              disabled={loading}
              className="bg-oracle-green hover:bg-oracle-green/80 text-white px-8 py-3 rounded-lg font-medium disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {loading ? "Iniciando..." : "Trading en Papel"}
            </button>
            <button
              onClick={() => initAgent("shadow")}
              disabled={loading}
              className="bg-yellow-500 hover:bg-yellow-600 text-white px-8 py-3 rounded-lg font-medium disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Modo Sombra
            </button>
          </div>
          {error && (
            <p className="text-oracle-red text-sm mt-4">{error}</p>
          )}
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-oracle-green/20 flex items-center justify-center">
                <svg className="w-5 h-5 text-oracle-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-oracle-text font-semibold">Aprendizaje Automático</h3>
            </div>
            <p className="text-oracle-muted text-sm">
              El agente aprende de los patrones del mercado y mejora continuamente sus estrategias
            </p>
          </div>
          <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                <svg className="w-5 h-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-oracle-text font-semibold">Modo Sombra</h3>
            </div>
            <p className="text-oracle-muted text-sm">
              Opera virtualmente sin riesgo mientras analizas las señales del agente
            </p>
          </div>
          <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-oracle-accent/20 flex items-center justify-center">
                <svg className="w-5 h-5 text-oracle-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <h3 className="text-oracle-text font-semibold">Rendimiento Superior</h3>
            </div>
            <p className="text-oracle-muted text-sm">
              Supera a las estrategias tradicionales de buy & hold
            </p>
          </div>
        </div>
      </div>
    );
  }

  const equityCurve = performance?.equity_curve || [];
  const isPositiveEquity = (performance?.total_pnl || 0) >= 0;

  return (
    <div className="space-y-4">
      {/* Header with status */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1.5 rounded-full text-sm font-bold text-white ${getModeColor(status?.mode || "paper")}`}>
              {getModeLabel(status?.mode || "paper")}
            </span>
          </div>
          <div>
            <h2 className="text-oracle-text text-xl font-bold">{status?.symbol || "BTC/USD"}</h2>
            <p className="text-oracle-muted text-xs">
              {status?.model_loaded ? "Modelo cargado" : "Sin modelo (señal simple)"}
            </p>
          </div>
        </div>
        
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => updateMode("paper")}
            disabled={loading || status?.mode === "paper"}
            className="bg-oracle-green/20 hover:bg-oracle-green/40 text-oracle-green px-4 py-2 rounded-lg text-sm disabled:opacity-50 transition-colors"
          >
            Papel
          </button>
          <button
            onClick={() => updateMode("shadow")}
            disabled={loading || status?.mode === "shadow"}
            className="bg-yellow-500/20 hover:bg-yellow-500/40 text-yellow-500 px-4 py-2 rounded-lg text-sm disabled:opacity-50 transition-colors"
          >
            Sombra
          </button>
          <button
            onClick={() => updateMode("live")}
            disabled={loading || status?.mode === "live"}
            className="bg-oracle-red/20 hover:bg-oracle-red/40 text-oracle-red px-4 py-2 rounded-lg text-sm disabled:opacity-50 transition-colors"
          >
            Real
          </button>
        </div>
      </div>

      {/* Signal Panel */}
      <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-oracle-text font-semibold">Señal de Trading</h3>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-oracle-muted cursor-pointer">
              <input
                type="checkbox"
                checked={autoTrade}
                onChange={(e) => setAutoTrade(e.target.checked)}
                className="w-4 h-4 rounded border-oracle-border bg-oracle-bg text-oracle-accent"
              />
              Auto-trade
            </label>
          </div>
        </div>
        
        {signal ? (
          <div className="space-y-4" key={signalKey}>
            {/* Last Update */}
            {lastUpdate && (
              <div className="text-xs text-oracle-muted text-right">
                Última actualización: {lastUpdate.toLocaleTimeString()}
              </div>
            )}
            {/* Current Price */}
            {(currentPrice || signal.current_price) && (
              <div className="bg-oracle-bg rounded p-3 flex items-center justify-between">
                <div>
                  <p className="text-oracle-muted text-xs">Precio Actual BTC</p>
                  <p className="text-2xl font-bold text-oracle-text font-mono">
                    ${(currentPrice || signal.current_price || 0).toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-oracle-muted text-xs">Señal</p>
                  <p className={`text-xl font-bold ${
                    signal.action === "buy" ? "text-oracle-green" : 
                    signal.action === "sell" ? "text-oracle-red" : "text-oracle-muted"
                  }`}>
                    {signal.action?.toUpperCase() || "HOLD"}
                  </p>
                </div>
              </div>
            )}
            
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="bg-oracle-bg rounded p-3">
                <p className="text-oracle-muted text-xs">Acción</p>
                <p className={`text-xl font-bold ${
                  signal.action === "buy" ? "text-oracle-green" : 
                  signal.action === "sell" ? "text-oracle-red" : "text-oracle-muted"
                }`}>
                  {signal.action?.toUpperCase() || "HOLD"}
                </p>
              </div>
              <div className="bg-oracle-bg rounded p-3">
                <p className="text-oracle-muted text-xs">Precio Entrada</p>
                <p className="text-xl font-bold text-oracle-text font-mono">
                  {signal.entry_price && signal.entry_price > 0 
                    ? `$${signal.entry_price.toLocaleString()}`
                    : signal.current_price 
                      ? `$${signal.current_price.toLocaleString()}`
                      : '-'}
                </p>
              </div>
              <div className="bg-oracle-bg rounded p-3">
                <p className="text-oracle-muted text-xs">Momentum</p>
                <p className={`text-xl font-bold ${getPnlColor(signal.momentum || 0)}`}>
                  {fmtPct((signal.momentum || 0) * 100)}
                </p>
              </div>
              <div className="bg-oracle-bg rounded p-3">
                <p className="text-oracle-muted text-xs">RSI</p>
                <p className="text-xl font-bold text-oracle-text">
                  {fmtNum(signal.rsi, 0)}
                </p>
              </div>
              <div className="bg-oracle-bg rounded p-3">
                <p className="text-oracle-muted text-xs">Confianza</p>
                <p className="text-xl font-bold text-oracle-accent">
                  {fmtNum((signal.confidence || 0) * 100, 0)}%
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-oracle-muted text-sm mb-4">
            Obtén una señal de trading del agente
          </p>
        )}
        
        <div className="flex gap-2 mt-4">
          <button
            onClick={fetchSignal}
            disabled={loading}
            className="bg-oracle-accent hover:bg-oracle-accent/80 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {loading ? "Analizando..." : "Obtener Señal"}
          </button>
          
          {signal && signal.action !== "hold" && (
            <button
              onClick={executeTrade}
              disabled={loading}
              className={`px-4 py-2 rounded-lg text-sm disabled:opacity-50 transition-colors flex items-center gap-2 ${
                signal.action === "buy" 
                  ? "bg-oracle-green hover:bg-oracle-green/80 text-white" 
                  : "bg-oracle-red hover:bg-oracle-red/80 text-white"
              }`}
            >
              {signal.action === "buy" ? "Comprar" : "Vender"}
            </button>
          )}
        </div>
        
        {signal?.reason && (
          <p className="text-oracle-muted text-xs mt-3">
            {signal.reason}
          </p>
        )}
        
        {error && (
          <p className="text-oracle-red text-sm mt-3">{error}</p>
        )}
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Position & Price */}
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <p className="text-oracle-muted text-xs uppercase tracking-wide mb-1">Posición Actual</p>
          <p className={`text-2xl font-bold ${getPositionColor(status?.position || 0)}`}>
            {getPositionLabel(status?.position || 0)}
          </p>
          <p className="text-oracle-muted text-xs mt-1">
            {status?.entry_price && status.entry_price > 0 ? `Entrada: $${status.entry_price.toLocaleString()}` : "Sin posición"}
          </p>
        </div>

        {/* P&L */}
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <p className="text-oracle-muted text-xs uppercase tracking-wide mb-1">P&L No Realizado</p>
          <p className={`text-2xl font-bold font-mono ${getPnlColor(status?.unrealized_pnl || 0)}`}>
            {fmtMoney(status?.unrealized_pnl)}
          </p>
          <p className={`text-xs mt-1 ${getPnlColor(status?.unrealized_pnl_pct || 0)}`}>
            {fmtPct(status?.unrealized_pnl_pct)}
          </p>
        </div>

        {/* Total P&L */}
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <p className="text-oracle-muted text-xs uppercase tracking-wide mb-1">P&L Total</p>
          <p className={`text-2xl font-bold font-mono ${getPnlColor(performance?.total_pnl || 0)}`}>
            {fmtMoney(performance?.total_pnl)}
          </p>
          <p className={`text-xs mt-1 ${getPnlColor(performance?.total_pnl_pct || 0)}`}>
            {fmtPct(performance?.total_pnl_pct)}
          </p>
        </div>

        {/* Win Rate */}
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <p className="text-oracle-muted text-xs uppercase tracking-wide mb-1">Tasa de Aciertos</p>
          <p className={`text-2xl font-bold ${getPnlColor((performance?.win_rate || 0) - 0.5)}`}>
            {fmtNum((performance?.win_rate || 0) * 100, 1)}%
          </p>
          <p className="text-oracle-muted text-xs mt-1">
            {performance?.winning_trades || 0} / {(performance?.total_trades || 0)}
          </p>
        </div>
      </div>

      {/* Equity Curve & Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Equity Curve Chart */}
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-oracle-text font-semibold">Curva de Equity</h3>
            <span className="text-oracle-muted text-xs">
              Balance: {fmtMoney(performance?.current_estimate)}
            </span>
          </div>
          {equityCurve.length > 1 ? (
            <div className="h-48">
              <SparklineChart 
                data={equityCurve} 
                positive={isPositiveEquity}
                height={180}
              />
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-oracle-muted">
              <p>Iniciando curva de equity...</p>
            </div>
          )}
        </div>

        {/* Quick Stats */}
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <h3 className="text-oracle-text font-semibold mb-4">Estadísticas</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-oracle-muted text-sm">Operaciones Totales</span>
              <span className="text-oracle-text font-bold">{performance?.total_trades || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-oracle-muted text-sm">Ganadoras</span>
              <span className="text-oracle-green font-bold">{performance?.winning_trades || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-oracle-muted text-sm">Perdedoras</span>
              <span className="text-oracle-red font-bold">{performance?.losing_trades || 0}</span>
            </div>
            <div className="border-t border-oracle-border my-2" />
            <div className="flex justify-between items-center">
              <span className="text-oracle-muted text-sm">Mejor Operación</span>
              <span className="text-oracle-green font-bold font-mono">{fmtMoney(performance?.best_trade)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-oracle-muted text-sm">Peor Operación</span>
              <span className="text-oracle-red font-bold font-mono">{fmtMoney(performance?.worst_trade)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-oracle-muted text-sm">Factor de Profit</span>
              <span className="text-oracle-text font-bold font-mono">{fmtNum(performance?.profit_factor)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-oracle-muted text-sm">Drawdown Máximo</span>
              <span className="text-oracle-red font-bold font-mono">{fmtPct(performance?.max_drawdown)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Settings & Recent Trades */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Risk Settings */}
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <h3 className="text-oracle-text font-semibold mb-4">Configuración de Riesgo</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-oracle-muted text-sm">Posición Máxima</span>
                <span className="text-oracle-text font-medium">{fmtNum((status?.max_position_pct || 0.1) * 100, 0)}%</span>
              </div>
              <div className="h-2 bg-oracle-bg rounded-full overflow-hidden">
                <div className="h-full bg-oracle-accent" style={{ width: `${(status?.max_position_pct || 0.1) * 100}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-oracle-muted text-sm">Stop Loss</span>
                <span className="text-oracle-red font-medium">{fmtNum((status?.stop_loss_pct || 0.05) * 100, 0)}%</span>
              </div>
              <div className="h-2 bg-oracle-bg rounded-full overflow-hidden">
                <div className="h-full bg-oracle-red" style={{ width: `${(status?.stop_loss_pct || 0.05) * 100}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-oracle-muted text-sm">Take Profit</span>
                <span className="text-oracle-green font-medium">{fmtNum((status?.take_profit_pct || 0.1) * 100, 0)}%</span>
              </div>
              <div className="h-2 bg-oracle-bg rounded-full overflow-hidden">
                <div className="h-full bg-oracle-green" style={{ width: `${(status?.take_profit_pct || 0.1) * 100}%` }} />
              </div>
            </div>
          </div>

          {(status?.position || 0) !== 0 && (
            <button
              onClick={closePosition}
              disabled={loading}
              className="w-full mt-4 bg-oracle-red/20 hover:bg-oracle-red/40 text-oracle-red px-4 py-2 rounded-lg text-sm disabled:opacity-50 transition-colors"
            >
              Cerrar Posición
            </button>
          )}
        </div>

        {/* Recent Trades */}
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4 lg:col-span-2">
          <h3 className="text-oracle-text font-semibold mb-4">Operaciones Recientes</h3>
          
          {(!trades || trades.length === 0) ? (
            <div className="text-center py-8 text-oracle-muted">
              <svg className="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p>Sin operaciones aún</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-oracle-muted border-b border-oracle-border">
                    <th className="text-left py-2">Fecha</th>
                    <th className="text-left py-2">Acción</th>
                    <th className="text-right py-2">Precio</th>
                    <th className="text-right py-2">Cantidad</th>
                    <th className="text-right py-2">Valor</th>
                    <th className="text-right py-2">P&L</th>
                    <th className="text-right py-2">Confianza</th>
                  </tr>
                </thead>
                <tbody>
                  {(trades || []).slice(-15).reverse().map((trade: any, i: number) => (
                    <tr key={i} className="border-b border-oracle-border/30 hover:bg-oracle-bg/50">
                      <td className="py-2 text-oracle-muted text-xs">
                        {trade.timestamp ? new Date(trade.timestamp).toLocaleDateString() : "-"}
                      </td>
                      <td className={`py-2 font-bold ${trade.action === "buy" ? "text-oracle-green" : "text-oracle-red"}`}>
                        {trade.action === "buy" ? "COMPRA" : "VENTA"}
                      </td>
                      <td className="py-2 text-right text-oracle-text font-mono">
                        {fmtMoney(trade.price)}
                      </td>
                      <td className="py-2 text-right text-oracle-text">
                        {fmtNum(trade.quantity, 6)}
                      </td>
                      <td className="py-2 text-right text-oracle-text font-mono">
                        {fmtMoney(trade.value)}
                      </td>
                      <td className={`py-2 text-right font-mono ${getPnlColor(trade.pnl || 0)}`}>
                        {fmtMoney(trade.pnl)}
                      </td>
                      <td className="py-2 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-12 h-1.5 bg-oracle-bg rounded-full overflow-hidden">
                            <div 
                              className={`h-full ${(trade.confidence || 0) > 0.5 ? "bg-oracle-green" : "bg-yellow-500"}`} 
                              style={{ width: `${(trade.confidence || 0) * 100}%` }} 
                            />
                          </div>
                          <span className="text-oracle-muted text-xs w-10 text-right">
                            {fmtNum((trade.confidence || 0) * 100, 0)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Time-based P&L */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <p className="text-oracle-muted text-xs uppercase tracking-wide mb-1">P&L Hoy</p>
          <p className={`text-xl font-bold font-mono ${getPnlColor(performance?.daily_pnl || 0)}`}>
            {fmtMoney(performance?.daily_pnl)}
          </p>
        </div>
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <p className="text-oracle-muted text-xs uppercase tracking-wide mb-1">P&L Esta Semana</p>
          <p className={`text-xl font-bold font-mono ${getPnlColor(performance?.weekly_pnl || 0)}`}>
            {fmtMoney(performance?.weekly_pnl)}
          </p>
        </div>
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
          <p className="text-oracle-muted text-xs uppercase tracking-wide mb-1">P&L Este Mes</p>
          <p className={`text-xl font-bold font-mono ${getPnlColor(performance?.monthly_pnl || 0)}`}>
            {fmtMoney(performance?.monthly_pnl)}
          </p>
        </div>
      </div>
    </div>
  );
}
