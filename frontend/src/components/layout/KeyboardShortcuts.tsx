"use client";

import { useEffect, useRef } from "react";

import { useView } from "@/contexts/ViewContext";
import type { SectionId } from "@/types";

const SECTION_KEYS: Record<string, SectionId> = {
  "1": "home",
  "2": "priorities",
  "3": "portfolio",
  "4": "research",
  "5": "markets",
  "6": "assistant",
};

export default function KeyboardShortcuts() {
  const {
    commandBarOpen,
    openAssetDetail,
    selectedSymbol,
    setActiveSection,
    setCommandBarOpen,
    sidebarCollapsed,
    setSidebarCollapsed,
  } = useView();
  const commandBarOpenRef = useRef(commandBarOpen);
  const sidebarCollapsedRef = useRef(sidebarCollapsed);

  useEffect(() => {
    commandBarOpenRef.current = commandBarOpen;
    sidebarCollapsedRef.current = sidebarCollapsed;
  }, [commandBarOpen, sidebarCollapsed]);

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandBarOpen(true);
        return;
      }

      if (event.key === "Escape" && commandBarOpenRef.current) {
        setCommandBarOpen(false);
        return;
      }

      if (isInput) return;

      if (event.shiftKey && event.key.toLowerCase() === "t") {
        event.preventDefault();
        openAssetDetail(selectedSymbol || undefined);
        return;
      }

      if (event.shiftKey && event.key.toLowerCase() === "p") {
        event.preventDefault();
        setActiveSection("priorities");
        return;
      }

      if (event.shiftKey && event.key.toLowerCase() === "m") {
        event.preventDefault();
        setActiveSection("markets");
        return;
      }

      if (event.key === "[") {
        event.preventDefault();
        setSidebarCollapsed(!sidebarCollapsedRef.current);
        return;
      }

      const section = SECTION_KEYS[event.key];
      if (section) {
        event.preventDefault();
        setActiveSection(section);
      }
    };

    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [openAssetDetail, selectedSymbol, setActiveSection, setCommandBarOpen, setSidebarCollapsed]);

  return null;
}
