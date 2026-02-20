"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

export type View =
  | "overview"
  | "analysis"
  | "screener"
  | "movers"
  | "volatility"
  | "commodities"
  | "paper-trade"
  | "rl-trading"
  | "connections"
  | "alerts"
  | "chat"
  | "macro"
  | "recommendations"
  | "prediction"
  | "calendar"
  | "heatmap"
  | "settings";

const STORAGE_KEY = "myinvestia-view";

function getStoredView(): View | null {
  if (typeof window === "undefined") return null;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (
      saved === "overview" ||
      saved === "analysis" ||
      saved === "screener" ||
      saved === "movers" ||
      saved === "volatility" ||
      saved === "commodities" ||
      saved === "paper-trade" ||
      saved === "rl-trading" ||
      saved === "connections" ||
      saved === "alerts" ||
      saved === "chat" ||
      saved === "macro" ||
      saved === "recommendations" ||
      saved === "prediction" ||
      saved === "calendar" ||
      saved === "heatmap" ||
      saved === "settings"
    ) {
      return saved;
    }
    return null;
  } catch {
    return null;
  }
}

interface ViewContextType {
  activeView: View;
  setActiveView: (view: View) => void;
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
  commandBarOpen: boolean;
  setCommandBarOpen: (open: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  sidebarMobileOpen: boolean;
  setSidebarMobileOpen: (open: boolean) => void;
}

const ViewContext = createContext<ViewContextType | null>(null);

export function ViewProvider({ children }: { children: ReactNode }) {
  const [activeView, setActiveView] = useState<View>(() => {
    return getStoredView() || "overview";
  });
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [commandBarOpen, setCommandBarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, activeView);
    } catch {}
  }, [activeView]);

  return (
    <ViewContext.Provider
      value={{
        activeView,
        setActiveView,
        selectedSymbol,
        setSelectedSymbol,
        commandBarOpen,
        setCommandBarOpen,
        sidebarCollapsed,
        setSidebarCollapsed,
        sidebarMobileOpen,
        setSidebarMobileOpen,
      }}
    >
      {children}
    </ViewContext.Provider>
  );
}

export function useView() {
  const ctx = useContext(ViewContext);
  if (!ctx) throw new Error("useView must be used within ViewProvider");
  return ctx;
}
