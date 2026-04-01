"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { useView } from "@/contexts/ViewContext";
import type { SectionId, SectionTabId } from "@/types";

interface CommandItem {
  id: string;
  label: string;
  category: string;
  action: () => void;
}

const SECTION_COMMANDS: Array<{
  id: string;
  label: string;
  category: string;
  section: SectionId;
  tab?: SectionTabId;
}> = [
  { id: "home", label: "Ir a Inicio", category: "Secciones", section: "home" },
  {
    id: "priorities",
    label: "Ir a Prioridades",
    category: "Secciones",
    section: "priorities",
  },
  {
    id: "portfolio",
    label: "Ir a Cartera",
    category: "Secciones",
    section: "portfolio",
  },
  {
    id: "research",
    label: "Ir a Investigación",
    category: "Secciones",
    section: "research",
  },
  { id: "markets", label: "Ir a Mercados", category: "Secciones", section: "markets" },
  {
    id: "assistant",
    label: "Ir a Asistente",
    category: "Secciones",
    section: "assistant",
  },
  {
    id: "portfolio-theses",
    label: "Abrir tesis de cartera",
    category: "Acciones",
    section: "portfolio",
    tab: "portfolio-theses",
  },
  {
    id: "markets-macro",
    label: "Abrir macro",
    category: "Acciones",
    section: "markets",
    tab: "markets-macro",
  },
  {
    id: "markets-calendar",
    label: "Abrir calendario",
    category: "Acciones",
    section: "markets",
    tab: "markets-calendar",
  },
  {
    id: "assistant-bot",
    label: "Abrir bot Telegram",
    category: "Acciones",
    section: "assistant",
    tab: "assistant-bot",
  },
  {
    id: "assistant-alerts",
    label: "Abrir alertas",
    category: "Acciones",
    section: "assistant",
    tab: "assistant-alerts",
  },
  {
    id: "settings",
    label: "Abrir ajustes",
    category: "Acciones",
    section: "settings",
  },
];

export default function CommandBar() {
  const {
    commandBarOpen,
    openAssetDetail,
    selectedSymbol,
    setActiveSection,
    setCommandBarOpen,
    setSelectedSymbol,
  } = useView();
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = useMemo<CommandItem[]>(
    () =>
      SECTION_COMMANDS.map((item) => ({
        id: item.id,
        label: item.label,
        category: item.category,
        action: () => setActiveSection(item.section, item.tab),
      })),
    [setActiveSection],
  );

  const normalizedQuery = query.trim().toUpperCase();
  const looksLikeSymbol = /^[A-Z][A-Z0-9.-]{0,9}$/.test(normalizedQuery);

  const allCommands = useMemo(() => {
    const symbolCommands: CommandItem[] = [];
    if (looksLikeSymbol) {
      symbolCommands.push({
        id: "lookup",
        label: `Abrir detalle de ${normalizedQuery}`,
        category: "Símbolo",
        action: () => {
          setSelectedSymbol(normalizedQuery);
          openAssetDetail(normalizedQuery);
        },
      });
    } else if (!query.trim() && selectedSymbol) {
      symbolCommands.push({
        id: "lookup-current",
        label: `Abrir detalle de ${selectedSymbol}`,
        category: "Símbolo",
        action: () => openAssetDetail(selectedSymbol),
      });
    }

    return [...symbolCommands, ...commands];
  }, [commands, looksLikeSymbol, normalizedQuery, openAssetDetail, query, selectedSymbol, setSelectedSymbol]);

  const filtered = useMemo(
    () =>
      allCommands.filter((command) =>
        `${command.label} ${command.category}`.toLowerCase().includes(query.toLowerCase()),
      ),
    [allCommands, query],
  );

  const closeCommandBar = () => {
    setQuery("");
    setCommandBarOpen(false);
  };

  useEffect(() => {
    if (!commandBarOpen) return;
    const frameId = window.requestAnimationFrame(() => {
      inputRef.current?.focus();
    });
    return () => window.cancelAnimationFrame(frameId);
  }, [commandBarOpen]);

  const execute = (command: CommandItem) => {
    command.action();
    closeCommandBar();
  };

  if (!commandBarOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[16vh]">
      <button
        type="button"
        className="fixed inset-0 bg-black/60"
        onClick={closeCommandBar}
        aria-label="Close command bar"
      />
      <div
        className="relative w-full max-w-2xl overflow-hidden rounded-2xl border border-oracle-border bg-oracle-panel shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label="Command bar"
      >
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") closeCommandBar();
            if (event.key === "Enter" && filtered.length > 0) execute(filtered[0]);
          }}
          placeholder="Escribe una sección, una acción o un símbolo..."
          className="w-full border-b border-oracle-border bg-transparent px-4 py-3 text-sm text-oracle-text placeholder:text-oracle-muted focus:outline-none"
        />
        <div className="max-h-80 overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <p className="px-4 py-2 text-sm text-oracle-muted">
              Sin resultados. Prueba con `Prioridades`, `Mercados` o un símbolo como `NVDA`.
            </p>
          ) : null}
          {filtered.map((command) => (
            <button
              key={command.id}
              onClick={() => execute(command)}
              className="flex w-full items-center justify-between px-4 py-3 text-left text-sm text-oracle-text transition-colors hover:bg-oracle-bg"
            >
              <span>{command.label}</span>
              <span className="text-xs text-oracle-muted">{command.category}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
