import { useState, useCallback, useEffect } from "react";
import { fetchAPI, postAPI } from "@/lib/api";

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

interface Trade {
  id?: string;
  action: string;
  price: number;
  quantity: number;
  value: number;
  pnl?: number;
  timestamp?: string;
}

interface SignalResponse {
  signal?: Signal;
  current_price?: number;
  executed?: boolean;
}

interface AgentStatus {
  mode: string;
  symbol: string;
  position: number;
  entry_price?: number;
  current_price?: number;
  balance?: number;
  model_loaded?: boolean;
}

interface Performance {
  total_trades: number;
  winning_trades: number;
  total_pnl: number;
  win_rate: number;
  equity_curve?: number[];
}

interface Props {
  initialMode?: string;
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
  const [tradeMessage, setTradeMessage] = useState<{type: 'success' | 'error'; text: string} | null>(null);

  const api = fetchAPI;
  const post = postAPI;

  const fetchStatus = useCallback(async () => {
    try {
      const data = await api<AgentStatus>("/rl-agent/status");
      setStatus(data);
      if (data && data.position !== undefined) {
        setIsInitialized(true);
      }
    } catch (e) {
      console.error("Error fetching status:", e);
    }
  }, [api]);

  const fetchPerformance = useCallback(async () => {
    try {
      const data = await api<Performance>("/rl-agent/performance");
      setPerformance(data);
    } catch (e) {
      console.error("Error fetching performance:", e);
    }
  }, [api]);

  const fetchTrades = useCallback(async () => {
    try {
      const data = await api<any>("/rl-agent/trades?limit=50");
      const tradesData = Array.isArray(data) ? data : (data?.trades || []);
      setTrades(tradesData);
    } catch (e) {
      console.error("Error fetching trades:", e);
      setTrades([]);
    }
  }, [api]);

  const fetchSignal = useCallback(async () => {
    setTradeMessage(null);
    try {
      setLoading(true);
      setError(null);
      const data = await post<Signal>("/rl-agent/signal", {
        data: [],
        current_price: 45000,
        _t: Date.now(),
      });
      setSignal(data);
      setLastUpdate(new Date());
      
      const price = data.current_price;
      if (price) {
        setCurrentPrice(price);
      }
      
      // Auto-trade: ejecutar automáticamente si hay señal clara
      if (autoTrade && data.action !== "hold" && data.confidence >= 0.4) {
        const result = await post<SignalResponse>("/rl-agent/trade", {
          data: [],
          current_price: data.current_price || 45000,
        });
        
        if (result.executed) {
          setTradeMessage({ type: 'success', text: `Operación ${data.action === 'buy' ? 'COMPRA' : 'VENTA'} ejecutada automáticamente` });
          await fetchStatus();
          await fetchPerformance();
          await fetchTrades();
        }
      }
    } catch (e: any) {
      console.error("Error fetching signal:", e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [post, autoTrade, fetchStatus, fetchPerformance, fetchTrades]);

  const initAgent = async (mode: string) => {
    setLoading(true);
    setError(null);
    try {
      await post("/rl-agent/init", {
        symbol: "BTC/USD",
        mode,
        initial_balance: 10000,
        max_position_pct: 0.1,
        stop_loss_pct: 0.05,
        take_profit_pct: 0.1,
      });
      setIsInitialized(true);
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
    setTradeMessage(null);
    try {
      const price = currentPrice || signal?.current_price || 45000;
      const result = await post<SignalResponse>("/rl-agent/trade", {
        data: [],
        current_price: price,
      });
      
      if (result.executed) {
        const action = signal?.action === 'buy' ? 'COMPRADO' : 'VENDIDO';
        setTradeMessage({ type: 'success', text: `✅ ${action} a $${price.toLocaleString()}` });
        await fetchStatus();
        await fetchPerformance();
        await fetchTrades();
      } else if (result.signal?.reason) {
        setTradeMessage({ type: 'error', text: result.signal.reason });
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
    }, 300000);

    return () => clearInterval(interval);
  }, [isInitialized, autoTrade, fetchSignal, fetchStatus, fetchPerformance, fetchTrades]);

  const getPnlColor = (pnl: number) => {
    if (pnl > 0) return "text-oracle-green";
    if (pnl < 0) return "text-oracle-red";
    return "text-oracle-muted";
  };

  const fmtMoney = (n: number | undefined | null) => {
    if (n === undefined || n === null) return "-";
    return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  // NOT INITIALIZED STATE
  if (!isInitialized) {
    return (
      <div className="space-y-6">
        <div className="text-center py-8">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-oracle-accent/20 mb-4">
            <svg className="w-10 h-10 text-oracle-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-oracle-text mb-2">Agente de Trading IA</h2>
          <p className="text-oracle-muted mb-8">Inicia el agente para comenzar a operar con señales automáticas</p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => initAgent("paper")}
              disabled={loading}
              className="bg-oracle-green hover:bg-oracle-green/80 text-white px-8 py-4 rounded-xl font-bold text-lg disabled:opacity-50 transition-all transform hover:scale-105 flex items-center gap-3"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {loading ? "Iniciando..." : "Iniciar Trading en Papel"}
            </button>
          </div>

          {error && (
            <p className="text-oracle-red mt-4">{error}</p>
          )}

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12 max-w-3xl mx-auto">
            <div className="bg-oracle-panel border border-oracle-border rounded-xl p-4 text-left">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 rounded-lg bg-oracle-green/20 flex items-center justify-center">
                  <svg className="w-4 h-4 text-oracle-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <h3 className="text-oracle-text font-semibold">Señales en Tiempo Real</h3>
              </div>
              <p className="text-oracle-muted text-sm">Obtén señales de trading basadas en indicadores técnicos y momentum</p>
            </div>
            <div className="bg-oracle-panel border border-oracle-border rounded-xl p-4 text-left">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                  <svg className="w-4 h-4 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-oracle-text font-semibold">Auto-Trading</h3>
              </div>
              <p className="text-oracle-muted text-sm">El agente opera automáticamente cuando detecta buenas oportunidades</p>
            </div>
            <div className="bg-oracle-panel border border-oracle-border rounded-xl p-4 text-left">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 rounded-lg bg-oracle-accent/20 flex items-center justify-center">
                  <svg className="w-4 h-4 text-oracle-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="text-oracle-text font-semibold">Sin Riesgo</h3>
              </div>
              <p className="text-oracle-muted text-sm">Practica con dinero virtual antes de operar con dinero real</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const equityCurve = performance?.equity_curve || [];
  const isPositiveEquity = (performance?.total_pnl || 0) >= 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className={`px-4 py-2 rounded-full text-white font-bold ${
            status?.mode === 'paper' ? 'bg-oracle-green' :
            status?.mode === 'shadow' ? 'bg-yellow-500' : 'bg-oracle-red'
          }`}>
            {status?.mode === 'paper' ? '📄 PAPEL' : status?.mode === 'shadow' ? '👁️ SOMBRA' : '💰 REAL'}
          </div>
          <div>
            <h2 className="text-oracle-text text-xl font-bold">BTC/USD</h2>
            <p className="text-oracle-muted text-xs">
              {status?.position === 1 ? `Position: $${status.entry_price?.toLocaleString()}` : "Sin posición"}
            </p>
          </div>
        </div>
        
        {/* Auto-trade toggle */}
        <label className={`flex items-center gap-3 px-4 py-2 rounded-xl cursor-pointer transition-all ${
          autoTrade ? 'bg-oracle-accent/20 border-2 border-oracle-accent' : 'bg-oracle-panel border border-oracle-border'
        }`}>
          <div className="relative">
            <input
              type="checkbox"
              checked={autoTrade}
              onChange={(e) => setAutoTrade(e.target.checked)}
              className="sr-only"
            />
            <div className={`w-11 h-6 rounded-full transition-colors ${autoTrade ? 'bg-oracle-accent' : 'bg-oracle-border'}`}>
              <div className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform mt-0.5 ${autoTrade ? 'translate-x-5 ml-0.5' : 'translate-x-0.5'}`} />
            </div>
          </div>
          <span className="text-oracle-text font-medium">
            🤖 Auto-Trade {autoTrade && 'ON'}
          </span>
        </label>
      </div>

      {/* BIG SIGNAL CARD */}
      <div className={`rounded-2xl p-6 border-2 transition-all ${
        signal?.action === 'buy' ? 'bg-gradient-to-br from-oracle-green/20 to-transparent border-oracle-green' :
        signal?.action === 'sell' ? 'bg-gradient-to-br from-oracle-red/20 to-transparent border-oracle-red' :
        'bg-oracle-panel border-oracle-border'
      }`}>
        {/* Signal Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-4">
            {/* Signal Icon */}
            <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
              signal?.action === 'buy' ? 'bg-oracle-green' :
              signal?.action === 'sell' ? 'bg-oracle-red' : 'bg-oracle-border'
            }`}>
              {signal?.action === 'buy' ? (
                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
              ) : signal?.action === 'sell' ? (
                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              ) : (
                <svg className="w-8 h-8 text-oracle-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                </svg>
              )}
            </div>
            <div>
              <p className="text-oracle-muted text-sm">
                {lastUpdate ? `Actualizado: ${lastUpdate.toLocaleTimeString()}` : "Sin señal"}
              </p>
              <h2 className={`text-3xl font-bold ${
                signal?.action === 'buy' ? 'text-oracle-green' :
                signal?.action === 'sell' ? 'text-oracle-red' : 'text-oracle-muted'
              }`}>
                {signal?.action === 'buy' ? 'COMPRAR' : signal?.action === 'sell' ? 'VENDER' : 'MANTENER'}
              </h2>
            </div>
          </div>
          
          {/* Price */}
          <div className="text-right">
            <p className="text-oracle-muted text-sm">Precio BTC</p>
            <p className="text-3xl font-bold text-oracle-text font-mono">
              ${(currentPrice || signal?.current_price || 0).toLocaleString()}
            </p>
          </div>
        </div>

        {/* Indicators */}
        {signal && (
          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="bg-oracle-bg/50 rounded-lg p-3 text-center">
              <p className="text-oracle-muted text-xs mb-1">Confianza</p>
              <p className="text-xl font-bold text-oracle-accent">{Math.round((signal.confidence || 0) * 100)}%</p>
            </div>
            <div className="bg-oracle-bg/50 rounded-lg p-3 text-center">
              <p className="text-oracle-muted text-xs mb-1">RSI</p>
              <p className="text-xl font-bold text-oracle-text">{Math.round(signal.rsi || 0)}</p>
            </div>
            <div className="bg-oracle-bg/50 rounded-lg p-3 text-center">
              <p className="text-oracle-muted text-xs mb-1">Momentum</p>
              <p className={`text-xl font-bold ${getPnlColor((signal.momentum || 0) * 100)}`}>
                {((signal.momentum || 0) * 100).toFixed(2)}%
              </p>
            </div>
            <div className="bg-oracle-bg/50 rounded-lg p-3 text-center">
              <p className="text-oracle-muted text-xs mb-1">Tu Position</p>
              <p className="text-xl font-bold text-oracle-text">
                {status?.position === 1 ? 'LONG' : 'FLAT'}
              </p>
            </div>
          </div>
        )}

        {/* Reason */}
        {signal?.reason && (
          <p className="text-oracle-muted text-sm mb-4">{signal.reason}</p>
        )}

        {/* Trade Message */}
        {tradeMessage && (
          <div className={`mb-4 p-3 rounded-lg ${
            tradeMessage.type === 'success' ? 'bg-oracle-green/20 text-oracle-green' : 'bg-oracle-red/20 text-oracle-red'
          }`}>
            {tradeMessage.text}
          </div>
        )}

        {/* Action Button */}
        <div className="flex gap-3">
          <button
            onClick={fetchSignal}
            disabled={loading}
            className="flex-1 bg-oracle-accent hover:bg-oracle-accent/80 text-white px-6 py-3 rounded-xl font-bold disabled:opacity-50 transition-all flex items-center justify-center gap-2"
          >
            {loading ? (
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
            {loading ? "Analizando..." : "Obtener Nueva Señal"}
          </button>

          {signal && signal.action !== 'hold' && (
            <button
              onClick={executeTrade}
              disabled={loading}
              className={`px-8 py-3 rounded-xl font-bold disabled:opacity-50 transition-all ${
                signal.action === 'buy' 
                  ? 'bg-oracle-green hover:bg-oracle-green/80 text-white' 
                  : 'bg-oracle-red hover:bg-oracle-red/80 text-white'
              }`}
            >
              {signal.action === 'buy' ? '✅ COMPRAR' : '✅ VENDER'}
            </button>
          )}
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-oracle-panel border border-oracle-border rounded-xl p-4">
          <p className="text-oracle-muted text-xs mb-1">Balance</p>
          <p className="text-xl font-bold text-oracle-text">${(status?.balance || 10000).toLocaleString()}</p>
        </div>
        <div className="bg-oracle-panel border border-oracle-border rounded-xl p-4">
          <p className="text-oracle-muted text-xs mb-1">Total P&L</p>
          <p className={`text-xl font-bold ${getPnlColor(performance?.total_pnl || 0)}`}>
            ${(performance?.total_pnl || 0).toLocaleString()}
          </p>
        </div>
        <div className="bg-oracle-panel border border-oracle-border rounded-xl p-4">
          <p className="text-oracle-muted text-xs mb-1">Operaciones</p>
          <p className="text-xl font-bold text-oracle-text">{performance?.total_trades || 0}</p>
        </div>
        <div className="bg-oracle-panel border border-oracle-border rounded-xl p-4">
          <p className="text-oracle-muted text-xs mb-1">Win Rate</p>
          <p className="text-xl font-bold text-oracle-accent">{Math.round(performance?.win_rate || 0)}%</p>
        </div>
      </div>

      {/* Recent Trades */}
      {trades && trades.length > 0 && (
        <div className="bg-oracle-panel border border-oracle-border rounded-xl p-4">
          <h3 className="text-oracle-text font-semibold mb-3">Operaciones Recientes</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {trades.slice(-10).reverse().map((trade: any, i: number) => (
              <div key={i} className="flex items-center justify-between bg-oracle-bg rounded-lg px-3 py-2">
                <div className="flex items-center gap-3">
                  <span className={`font-bold ${trade.action === 'buy' ? 'text-oracle-green' : 'text-oracle-red'}`}>
                    {trade.action === 'buy' ? '🟢 COMPRA' : '🔴 VENTA'}
                  </span>
                  <span className="text-oracle-muted text-sm">
                    {trade.timestamp ? new Date(trade.timestamp).toLocaleDateString() : ""}
                  </span>
                </div>
                <div className="text-right">
                  <p className="text-oracle-text font-mono">${trade.price?.toLocaleString()}</p>
                  {trade.pnl !== undefined && (
                    <p className={`text-xs font-mono ${getPnlColor(trade.pnl)}`}>
                      {trade.pnl >= 0 ? '+' : ''}${trade.pnl?.toFixed(2)}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
