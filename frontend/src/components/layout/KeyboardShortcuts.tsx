"use client";

import { useEffect } from "react";
import { useView, type View } from "@/contexts/ViewContext";

const VIEW_KEYS: Record<string, View> = {
  "1": "overview",
  "2": "analysis",
  "3": "screener",
  "4": "movers",
  "5": "volatility",
  "6": "commodities",
  "7": "recommendations",
  "8": "chat",
  "9": "macro",
  "0": "alerts",
};

export default function KeyboardShortcuts() {
  const { setActiveView, setCommandBarOpen, commandBarOpen, sidebarCollapsed, setSidebarCollapsed } = useView();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;

      // Cmd+K / Ctrl+K for command bar
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandBarOpen(true);
        return;
      }

      // Escape closes command bar
      if (e.key === "Escape" && commandBarOpen) {
        setCommandBarOpen(false);
        return;
      }

      // Don't handle view shortcuts when typing in inputs
      if (isInput) return;

      // [ toggles sidebar
      if (e.key === "[") {
        e.preventDefault();
        setSidebarCollapsed(!sidebarCollapsed);
        return;
      }

      // Number keys for view switching
      const view = VIEW_KEYS[e.key];
      if (view) {
        e.preventDefault();
        setActiveView(view);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setActiveView, setCommandBarOpen, commandBarOpen, sidebarCollapsed, setSidebarCollapsed]);

  return null;
}
