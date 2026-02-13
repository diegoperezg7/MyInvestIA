"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

export type View =
  | "overview"
  | "analysis"
  | "screener"
  | "movers"
  | "volatility"
  | "commodities"
  | "paper-trade"
  | "alerts"
  | "chat"
  | "macro"
  | "recommendations";

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
  const [activeView, setActiveView] = useState<View>("overview");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [commandBarOpen, setCommandBarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false);

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
