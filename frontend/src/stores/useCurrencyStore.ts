import { create } from "zustand";
import { fetchAPI } from "@/lib/api";

export type Currency = "USD" | "EUR";

interface ConvertResult {
  amount: number;
  from: string;
  to: string;
  converted: number;
  rate: number;
  date: string;
}

interface CurrencyState {
  currency: Currency;
  rate: number;
  rateDate: string | null;
  loading: boolean;
  _hydrated: boolean;
  hydrate: () => void;
  setCurrency: (c: Currency) => void;
  toggleCurrency: () => void;
  fetchRate: () => Promise<void>;
  convert: (usdValue: number) => number;
  symbol: () => string;
  formatPrice: (usdValue: number, decimals?: number) => string;
}

const useCurrencyStore = create<CurrencyState>((set, get) => ({
  // Always start with EUR for SSR consistency (default currency)
  currency: "EUR",
  rate: 1.0,
  rateDate: null,
  loading: false,
  _hydrated: false,

  hydrate: () => {
    if (get()._hydrated) return;
    const saved = localStorage.getItem("oracle-currency") as Currency | null;
    if (saved && saved !== get().currency) {
      set({ currency: saved, _hydrated: true });
    } else {
      set({ _hydrated: true });
    }
    get().fetchRate();
  },

  setCurrency: (c) => {
    localStorage.setItem("oracle-currency", c);
    set({ currency: c });
    get().fetchRate();
  },

  toggleCurrency: () => {
    const next = get().currency === "USD" ? "EUR" : "USD";
    localStorage.setItem("oracle-currency", next);
    set({ currency: next });
    get().fetchRate();
  },

  fetchRate: async () => {
    const { currency } = get();
    if (currency === "USD") {
      set({ rate: 1.0, rateDate: null, loading: false });
      return;
    }
    set({ loading: true });
    try {
      const res = await fetchAPI<ConvertResult>(
        `/api/v1/market/convert?amount=1&from=USD&to=${currency}`
      );
      set({ rate: res.rate, rateDate: res.date, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  convert: (usdValue) => {
    return usdValue * get().rate;
  },

  symbol: () => {
    return get().currency === "USD" ? "$" : "\u20AC";
  },

  formatPrice: (usdValue, decimals = 2) => {
    const { currency, rate } = get();
    const converted = usdValue * rate;
    return new Intl.NumberFormat(currency === "USD" ? "en-US" : "de-DE", {
      style: "currency",
      currency,
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(converted);
  },
}));

export default useCurrencyStore;
