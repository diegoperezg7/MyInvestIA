"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Link2,
  Plus,
  RefreshCw,
  Trash2,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Loader2,
  Wifi,
  X,
} from "lucide-react";
import { fetchAPI, postAPI, deleteAPI } from "@/lib/api";
import useLanguageStore from "@/stores/useLanguageStore";
import type {
  ConnectionSummary,
  ConnectionList,
  SupportedProvider,
  SyncResult,
  ConnectionType,
} from "@/types";

// --- Provider logos ---
const PROVIDER_LOGOS: Record<string, string> = {
  // Exchanges
  binance: "/logos/binance.png",
  coinbase: "/logos/coinbase.png",
  kraken: "/logos/kraken.png",
  kucoin: "/logos/kucoin.png",
  bybit: "/logos/bybit.png",
  okx: "/logos/okx.png",
  gateio: "/logos/gateio.png",
  bitfinex: "/logos/bitfinex.png",
  gemini: "/logos/gemini.png",
  cryptocom: "/logos/cryptocom.png",
  htx: "/logos/htx.png",
  bitget: "/logos/bitget.png",
  mexc: "/logos/mexc.png",
  // Wallets
  metamask: "/logos/metamask.png",
  trustwallet: "/logos/trustwallet.png",
  coinbase_wallet: "/logos/coinbase_wallet.png",
  ledger: "/logos/ledger.png",
  rainbow: "/logos/rainbow.png",
  phantom: "/logos/phantom.png",
  // Brokers
  etoro: "/logos/etoro.png",
  ibkr: "/logos/ibkr.png",
  robinhood: "/logos/robinhood.png",
  trading212: "/logos/trading212.png",
  degiro: "/logos/degiro.png",
  xtb: "/logos/xtb.png",
  revolut: "/logos/revolut.png",
  plus500: "/logos/plus500.png",
  schwab: "/logos/schwab.png",
  fidelity: "/logos/fidelity.png",
  n26: "/logos/n26.png",
  // Prediction
  polymarket: "/logos/polymarket.png",
  kalshi: "/logos/kalshi.png",
};

const PROVIDER_FALLBACK: Record<string, string> = {
  // Exchanges
  binance: "B",
  coinbase: "CB",
  kraken: "K",
  kucoin: "KC",
  bybit: "BB",
  okx: "OK",
  gateio: "G",
  bitfinex: "BF",
  gemini: "G",
  cryptocom: "CC",
  htx: "HT",
  bitget: "BG",
  mexc: "MX",
  // Wallets
  metamask: "M",
  trustwallet: "TW",
  coinbase_wallet: "CW",
  ledger: "L",
  rainbow: "R",
  phantom: "PH",
  // Brokers
  etoro: "eT",
  ibkr: "IB",
  robinhood: "RH",
  trading212: "T2",
  degiro: "DG",
  xtb: "XT",
  revolut: "RV",
  plus500: "P5",
  schwab: "CS",
  fidelity: "FD",
  n26: "N2",
  // Prediction
  polymarket: "P",
  kalshi: "KA",
};

const PROVIDER_COLORS: Record<string, string> = {
  // Exchanges
  binance: "bg-yellow-500/20 text-yellow-400",
  coinbase: "bg-blue-500/20 text-blue-400",
  kraken: "bg-purple-500/20 text-purple-400",
  kucoin: "bg-emerald-500/20 text-emerald-400",
  bybit: "bg-orange-500/20 text-orange-400",
  okx: "bg-slate-500/20 text-slate-300",
  gateio: "bg-blue-500/20 text-blue-300",
  bitfinex: "bg-green-500/20 text-green-400",
  gemini: "bg-cyan-500/20 text-cyan-300",
  cryptocom: "bg-blue-600/20 text-blue-400",
  htx: "bg-blue-500/20 text-blue-400",
  bitget: "bg-sky-500/20 text-sky-400",
  mexc: "bg-blue-500/20 text-blue-300",
  // Wallets
  metamask: "bg-orange-500/20 text-orange-400",
  trustwallet: "bg-blue-500/20 text-blue-400",
  coinbase_wallet: "bg-blue-500/20 text-blue-300",
  ledger: "bg-slate-500/20 text-slate-300",
  rainbow: "bg-pink-500/20 text-pink-400",
  phantom: "bg-purple-500/20 text-purple-400",
  // Brokers
  etoro: "bg-green-500/20 text-green-400",
  ibkr: "bg-red-500/20 text-red-400",
  robinhood: "bg-green-500/20 text-green-300",
  trading212: "bg-blue-500/20 text-blue-400",
  degiro: "bg-cyan-500/20 text-cyan-400",
  xtb: "bg-green-500/20 text-green-400",
  revolut: "bg-violet-500/20 text-violet-400",
  plus500: "bg-sky-500/20 text-sky-400",
  schwab: "bg-blue-600/20 text-blue-400",
  fidelity: "bg-green-600/20 text-green-400",
  n26: "bg-teal-500/20 text-teal-400",
  // Prediction
  polymarket: "bg-cyan-500/20 text-cyan-400",
  kalshi: "bg-indigo-500/20 text-indigo-400",
};

const STATUS_CONFIG: Record<string, { icon: typeof CheckCircle2; color: string; bg: string }> = {
  active: { icon: CheckCircle2, color: "text-oracle-green", bg: "bg-oracle-green/10" },
  pending: { icon: Clock, color: "text-yellow-400", bg: "bg-yellow-500/10" },
  error: { icon: XCircle, color: "text-oracle-red", bg: "bg-oracle-red/10" },
  disconnected: { icon: AlertTriangle, color: "text-oracle-muted", bg: "bg-oracle-muted/10" },
};

const TYPE_LABELS: Record<ConnectionType, { es: string; en: string }> = {
  exchange: { es: "Exchange", en: "Exchange" },
  wallet: { es: "Wallet", en: "Wallet" },
  broker: { es: "Broker", en: "Broker" },
  prediction: { es: "Prediccion", en: "Prediction" },
};

// --- Status Badge ---
function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.disconnected;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.color}`}>
      <Icon size={12} />
      {status}
    </span>
  );
}

// --- Provider Logo ---
function ProviderLogo({ provider, size = 40 }: { provider: string; size?: number }) {
  const logo = PROVIDER_LOGOS[provider];
  const fallback = PROVIDER_FALLBACK[provider] || provider[0]?.toUpperCase() || "?";
  const colors = PROVIDER_COLORS[provider] || "bg-oracle-border text-oracle-text";
  const [imgError, setImgError] = useState(false);

  if (logo && !imgError) {
    return (
      <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0">
        <img
          src={logo}
          alt={provider}
          width={size}
          height={size}
          className="w-full h-full object-cover rounded-lg"
          onError={() => setImgError(true)}
        />
      </div>
    );
  }

  return (
    <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm flex-shrink-0 ${colors}`}>
      {fallback}
    </div>
  );
}

// --- Connection Card ---
function ConnectionCard({
  conn,
  onSync,
  onDelete,
  onTest,
  syncing,
}: {
  conn: ConnectionSummary;
  onSync: (id: string) => void;
  onDelete: (id: string) => void;
  onTest: (id: string) => void;
  syncing: boolean;
}) {
  const { t } = useLanguageStore();
  const lastSync = conn.last_sync_at
    ? new Date(conn.last_sync_at).toLocaleString()
    : t("conn.never_synced");

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4 hover:border-oracle-accent/30 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <ProviderLogo provider={conn.provider} />
          <div>
            <h3 className="text-oracle-text font-semibold text-sm">{conn.label}</h3>
            <p className="text-oracle-muted text-xs capitalize">{conn.provider}</p>
          </div>
        </div>
        <StatusBadge status={conn.status} />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs mb-3">
        <div>
          <p className="text-oracle-muted">{t("conn.holdings")}</p>
          <p className="text-oracle-text font-medium">{conn.holdings_count}</p>
        </div>
        <div>
          <p className="text-oracle-muted">{t("conn.syncs")}</p>
          <p className="text-oracle-text font-medium">{conn.sync_count}</p>
        </div>
        <div className="col-span-2">
          <p className="text-oracle-muted">{t("conn.last_sync")}</p>
          <p className="text-oracle-text font-medium text-[11px]">{lastSync}</p>
        </div>
      </div>

      {conn.last_sync_error && (
        <p className="text-oracle-red text-xs mb-3 truncate" title={conn.last_sync_error}>
          {conn.last_sync_error}
        </p>
      )}

      <div className="flex items-center gap-2 border-t border-oracle-border pt-3">
        <button
          onClick={() => onSync(conn.id)}
          disabled={syncing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-oracle-accent/10 text-oracle-accent hover:bg-oracle-accent/20 transition-colors disabled:opacity-50"
        >
          {syncing ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          {t("conn.sync")}
        </button>
        <button
          onClick={() => onTest(conn.id)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-oracle-panel-hover text-oracle-muted hover:text-oracle-text transition-colors"
        >
          <Wifi size={12} />
          {t("conn.test")}
        </button>
        <div className="flex-1" />
        <button
          onClick={() => onDelete(conn.id)}
          className="p-1.5 rounded-md text-oracle-muted hover:text-oracle-red hover:bg-oracle-red/10 transition-colors"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

// --- Add Connection Modal ---
function AddConnectionModal({
  providers,
  onClose,
  onCreated,
}: {
  providers: SupportedProvider[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const { t } = useLanguageStore();
  const [tab, setTab] = useState<ConnectionType>("exchange");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [provider, setProvider] = useState("binance");
  const [label, setLabel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [address, setAddress] = useState("");
  const [chain, setChain] = useState("ethereum");

  const tabs: { key: ConnectionType; label: string; icon: string }[] = [
    { key: "exchange", label: "Exchanges", icon: "/logos/binance.png" },
    { key: "wallet", label: "Wallets", icon: "/logos/metamask.png" },
    { key: "broker", label: "Brokers", icon: "/logos/etoro.png" },
    { key: "prediction", label: "Prediction", icon: "/logos/polymarket.png" },
  ];

  const filteredProviders = providers.filter((p) => p.type === tab);

  // Set default provider when tab changes
  useEffect(() => {
    if (filteredProviders.length > 0 && !filteredProviders.find((p) => p.id === provider)) {
      setProvider(filteredProviders[0].id);
    }
  }, [tab, filteredProviders, provider]);

  const resetForm = () => {
    setLabel("");
    setApiKey("");
    setApiSecret("");
    setPassphrase("");
    setAddress("");
    setChain("ethereum");
    setError(null);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      if (tab === "exchange") {
        await postAPI("/api/v1/connections/exchange", {
          provider,
          label: label || `${provider} account`,
          api_key: apiKey,
          api_secret: apiSecret,
          passphrase: passphrase || undefined,
        });
      } else if (tab === "wallet") {
        await postAPI("/api/v1/connections/wallet", {
          provider,
          label: label || `${provider} (${chain})`,
          address,
          chain,
        });
      } else if (tab === "broker") {
        await postAPI("/api/v1/connections/broker", {
          provider,
          label: label || provider,
          api_key: apiKey,
          api_secret: apiSecret,
        });
      } else if (tab === "prediction") {
        await postAPI("/api/v1/connections/prediction", {
          provider,
          label: label || provider,
          wallet_address: address || undefined,
          api_key: apiKey || undefined,
        });
      }
      onCreated();
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create connection");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-oracle-panel border border-oracle-border rounded-xl w-full max-w-lg max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-oracle-border">
          <h2 className="text-oracle-text font-semibold">{t("conn.add_connection")}</h2>
          <button onClick={onClose} className="text-oracle-muted hover:text-oracle-text">
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-oracle-border">
          {tabs.map((tb) => (
            <button
              key={tb.key}
              onClick={() => { setTab(tb.key); resetForm(); }}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                tab === tb.key
                  ? "text-oracle-accent border-b-2 border-oracle-accent"
                  : "text-oracle-muted hover:text-oracle-text"
              }`}
            >
              <img src={tb.icon} alt={tb.label} className="w-4 h-4 rounded-sm" />
              {tb.label}
            </button>
          ))}
        </div>

        {/* Form */}
        <div className="p-4 space-y-3">
          {/* Label (shared) */}
          <div>
            <label className="text-oracle-muted text-xs mb-1 block">{t("conn.label")}</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder={t("conn.label_placeholder")}
              className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
            />
          </div>

          {tab === "exchange" && (
            <>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">{t("conn.provider")}</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                >
                  {filteredProviders.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">API Key</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter API key"
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                />
              </div>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">API Secret</label>
                <input
                  type="password"
                  value={apiSecret}
                  onChange={(e) => setApiSecret(e.target.value)}
                  placeholder="Enter API secret"
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                />
              </div>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">{t("conn.passphrase")}</label>
                <input
                  type="password"
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  placeholder={t("conn.passphrase_hint")}
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                />
              </div>
            </>
          )}

          {tab === "wallet" && (
            <>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">{t("conn.provider")}</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                >
                  {filteredProviders.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">Chain</label>
                <select
                  value={chain}
                  onChange={(e) => setChain(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                >
                  <option value="ethereum">Ethereum</option>
                  <option value="polygon">Polygon</option>
                  <option value="bsc">BSC</option>
                  <option value="arbitrum">Arbitrum</option>
                  <option value="optimism">Optimism</option>
                  <option value="base">Base</option>
                  <option value="avalanche">Avalanche</option>
                  {provider === "phantom" && <option value="solana">Solana</option>}
                </select>
              </div>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">{t("conn.wallet_address")}</label>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="0x..."
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm font-mono focus:outline-none focus:border-oracle-accent"
                />
              </div>
            </>
          )}

          {tab === "broker" && (
            <>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">{t("conn.provider")}</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                >
                  {filteredProviders.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <p className="text-oracle-muted text-xs">
                {filteredProviders.find((p) => p.id === provider)?.description || t("conn.etoro_note")}
              </p>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">API Key</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="API key"
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                />
              </div>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">API Secret</label>
                <input
                  type="password"
                  value={apiSecret}
                  onChange={(e) => setApiSecret(e.target.value)}
                  placeholder="API secret"
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                />
              </div>
            </>
          )}

          {tab === "prediction" && (
            <>
              <div>
                <label className="text-oracle-muted text-xs mb-1 block">{t("conn.provider")}</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                >
                  {filteredProviders.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              {provider === "kalshi" ? (
                <>
                  <div>
                    <label className="text-oracle-muted text-xs mb-1 block">API Key</label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Kalshi API key"
                      className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                    />
                  </div>
                  <div>
                    <label className="text-oracle-muted text-xs mb-1 block">API Secret</label>
                    <input
                      type="password"
                      value={apiSecret}
                      onChange={(e) => setApiSecret(e.target.value)}
                      placeholder="Kalshi API secret"
                      className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="text-oracle-muted text-xs mb-1 block">{t("conn.wallet_address")}</label>
                    <input
                      type="text"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      placeholder="0x... (Polygon)"
                      className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm font-mono focus:outline-none focus:border-oracle-accent"
                    />
                  </div>
                  <div>
                    <label className="text-oracle-muted text-xs mb-1 block">API Key ({t("conn.optional")})</label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Polymarket API key"
                      className="w-full px-3 py-2 rounded-md bg-oracle-bg border border-oracle-border text-oracle-text text-sm focus:outline-none focus:border-oracle-accent"
                    />
                  </div>
                </>
              )}
            </>
          )}

          {error && (
            <p className="text-oracle-red text-xs">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 p-4 border-t border-oracle-border">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md text-sm text-oracle-muted hover:text-oracle-text transition-colors"
          >
            {t("conn.cancel")}
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium bg-oracle-accent text-white hover:bg-oracle-accent/80 transition-colors disabled:opacity-50"
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            {t("conn.connect")}
          </button>
        </div>
      </div>
    </div>
  );
}

// --- Main View ---
export default function ConnectionsView() {
  const { t } = useLanguageStore();
  const [connections, setConnections] = useState<ConnectionSummary[]>([]);
  const [providers, setProviders] = useState<SupportedProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const loadConnections = useCallback(async () => {
    try {
      const data = await fetchAPI<ConnectionList>("/api/v1/connections/", { skipCache: true });
      setConnections(data.connections);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  const loadProviders = useCallback(async () => {
    try {
      const data = await fetchAPI<SupportedProvider[]>("/api/v1/connections/providers");
      setProviders(data);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadConnections();
    loadProviders();
  }, [loadConnections, loadProviders]);

  const handleSync = async (id: string) => {
    setSyncingId(id);
    setMessage(null);
    try {
      const result = await postAPI<SyncResult>(`/api/v1/connections/${id}/sync`, {});
      if (result.status === "success") {
        setMessage({ text: t("conn.sync_success", { count: String(result.holdings_synced) }), type: "success" });
      } else {
        setMessage({ text: result.error || t("conn.sync_failed"), type: "error" });
      }
      await loadConnections();
    } catch {
      setMessage({ text: t("conn.sync_failed"), type: "error" });
    } finally {
      setSyncingId(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingId("all");
    setMessage(null);
    try {
      const results = await postAPI<SyncResult[]>("/api/v1/connections/sync-all", {});
      const successes = results.filter((r) => r.status === "success").length;
      setMessage({ text: t("conn.sync_all_done", { count: String(successes), total: String(results.length) }), type: "success" });
      await loadConnections();
    } catch {
      setMessage({ text: t("conn.sync_failed"), type: "error" });
    } finally {
      setSyncingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t("conn.delete_confirm"))) return;
    try {
      await deleteAPI(`/api/v1/connections/${id}`);
      await loadConnections();
      setMessage({ text: t("conn.deleted"), type: "success" });
    } catch {
      setMessage({ text: t("conn.delete_failed"), type: "error" });
    }
  };

  const handleTest = async (id: string) => {
    try {
      const result = await postAPI<{ success: boolean; message: string }>(`/api/v1/connections/${id}/test`, {});
      setMessage({
        text: result.message,
        type: result.success ? "success" : "error",
      });
    } catch {
      setMessage({ text: t("conn.test_failed"), type: "error" });
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-oracle-border rounded w-48 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-oracle-panel border border-oracle-border rounded-lg p-4 h-48 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-oracle-text text-lg font-semibold flex items-center gap-2">
            <Link2 size={20} />
            {t("view.connections.title")}
          </h2>
          <p className="text-oracle-muted text-xs mt-0.5">{t("view.connections.desc")}</p>
        </div>
        <div className="flex items-center gap-2">
          {connections.length > 0 && (
            <button
              onClick={handleSyncAll}
              disabled={syncingId !== null}
              className="flex items-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium bg-oracle-panel border border-oracle-border text-oracle-muted hover:text-oracle-text transition-colors disabled:opacity-50"
            >
              {syncingId === "all" ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              {t("conn.sync_all")}
            </button>
          )}
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium bg-oracle-accent text-white hover:bg-oracle-accent/80 transition-colors"
          >
            <Plus size={14} />
            {t("conn.add")}
          </button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`p-3 rounded-lg text-sm ${
          message.type === "success" ? "bg-oracle-green/10 text-oracle-green" : "bg-oracle-red/10 text-oracle-red"
        }`}>
          {message.text}
        </div>
      )}

      {/* Connections grid */}
      {connections.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {connections.map((conn) => (
            <ConnectionCard
              key={conn.id}
              conn={conn}
              onSync={handleSync}
              onDelete={handleDelete}
              onTest={handleTest}
              syncing={syncingId === conn.id || syncingId === "all"}
            />
          ))}
        </div>
      ) : (
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-12 text-center">
          <Link2 size={40} className="mx-auto text-oracle-muted mb-3" />
          <h3 className="text-oracle-text font-semibold mb-1">{t("conn.empty_title")}</h3>
          <p className="text-oracle-muted text-sm mb-4">{t("conn.empty_desc")}</p>
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium bg-oracle-accent text-white hover:bg-oracle-accent/80 transition-colors"
          >
            <Plus size={14} />
            {t("conn.add_first")}
          </button>
        </div>
      )}

      {/* Add Connection Modal */}
      {showModal && (
        <AddConnectionModal
          providers={providers}
          onClose={() => setShowModal(false)}
          onCreated={loadConnections}
        />
      )}
    </div>
  );
}
