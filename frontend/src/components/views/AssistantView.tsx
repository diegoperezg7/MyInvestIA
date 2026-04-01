"use client";

import { useState } from "react";
import { BellRing, Bot, Link2, MessageSquareText, TestTube2 } from "lucide-react";

import NotificationsPanel from "@/components/dashboard/NotificationsPanel";
import SectionWorkspace from "@/components/layout/SectionWorkspace";
import AlertsView from "@/components/views/AlertsView";
import ChatView from "@/components/views/ChatView";
import ConnectionsView from "@/components/views/ConnectionsView";
import PaperTradingView from "@/components/views/PaperTradingView";
import RLTradingView from "@/components/views/RLTradingView";
import { SECTION_TABS, getSectionDescription } from "@/lib/shell";
import useLanguageStore from "@/stores/useLanguageStore";
import { useView } from "@/contexts/ViewContext";
import type { SectionTabId } from "@/types";

function assistantTabLabel(tab: SectionTabId, language: "es" | "en") {
  const tabCopy = SECTION_TABS.assistant.find((item) => item.id === tab);
  return tabCopy?.label[language] ?? tab;
}

export default function AssistantView() {
  const { activeTab, setActiveSection } = useView();
  const language = useLanguageStore((state) => state.language);
  const currentTab = activeTab.startsWith("assistant-")
    ? activeTab
    : "assistant-chat";
  const [labMode, setLabMode] = useState<"paper" | "rl">("paper");

  return (
    <SectionWorkspace
      eyebrow={language === "es" ? "Asistente" : "Assistant"}
      title={language === "es" ? "Explica, avisa y automatiza" : "Explain, alert and automate"}
      description={getSectionDescription("assistant", language)}
      tabs={SECTION_TABS.assistant.map((tab) => ({
        id: tab.id,
        label: assistantTabLabel(tab.id, language),
        hint: tab.description?.[language],
      }))}
      activeTab={currentTab}
      onTabChange={(tab) => setActiveSection("assistant", tab)}
      aside={
        <div className="grid gap-3 lg:grid-cols-4">
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <MessageSquareText className="h-4 w-4 text-oracle-accent" />
              Chat
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Preguntas directas con respuestas más claras y accionables."
                : "Direct questions with clearer and more actionable answers."}
            </p>
          </div>
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <Bot className="h-4 w-4 text-oracle-accent" />
              Telegram
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Tu bot personal para cartera, noticias y señales."
                : "Your personal bot for portfolio, news and signals."}
            </p>
          </div>
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <BellRing className="h-4 w-4 text-oracle-accent" />
              {language === "es" ? "Alertas" : "Alerts"}
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Reglas y escaneos para enterarte antes."
                : "Rules and scans so you know earlier."}
            </p>
          </div>
          <div className="rounded-2xl border border-oracle-border bg-oracle-bg/50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-oracle-text">
              <Link2 className="h-4 w-4 text-oracle-accent" />
              {language === "es" ? "Conexiones y lab" : "Connections & lab"}
            </div>
            <p className="mt-2 text-sm text-oracle-muted">
              {language === "es"
                ? "Integra cuentas y deja lo experimental fuera del flujo principal."
                : "Integrate accounts and keep experimental tools off the main flow."}
            </p>
          </div>
        </div>
      }
    >
      {currentTab === "assistant-chat" ? <ChatView /> : null}

      {currentTab === "assistant-bot" ? (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.88fr_1.12fr]">
          <NotificationsPanel />
          <div className="rounded-2xl border border-oracle-border bg-oracle-panel p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
              {language === "es" ? "Qué recibirás" : "What you will get"}
            </p>
            <div className="mt-4 space-y-3 text-sm text-oracle-text">
              <p>{language === "es" ? "Prioridades del inbox y catalizadores relevantes." : "Inbox priorities and relevant catalysts."}</p>
              <p>{language === "es" ? "Riesgos de cartera, tesis en riesgo y cambios de señal." : "Portfolio risk, at-risk theses and signal changes."}</p>
              <p>{language === "es" ? "Resúmenes premarket, cierre o ejecuciones manuales del bot." : "Premarket, close or manual bot runs."}</p>
            </div>
          </div>
        </div>
      ) : null}

      {currentTab === "assistant-alerts" ? <AlertsView /> : null}
      {currentTab === "assistant-connections" ? <ConnectionsView /> : null}

      {currentTab === "assistant-lab" ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-oracle-border bg-oracle-panel p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-oracle-muted">
                  {language === "es" ? "Laboratorio" : "Lab"}
                </p>
                <p className="mt-1 text-sm text-oracle-muted">
                  {language === "es"
                    ? "Herramientas avanzadas y beta. Úsalas si sabes exactamente lo que buscas."
                    : "Advanced and beta tools. Use them when you know exactly what you need."}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setLabMode("paper")}
                  className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                    labMode === "paper"
                      ? "border-oracle-accent/40 bg-oracle-accent/20 text-oracle-accent"
                      : "border-oracle-border text-oracle-muted hover:text-oracle-text"
                  }`}
                >
                  {language === "es" ? "Simulación" : "Paper trading"}
                </button>
                <button
                  onClick={() => setLabMode("rl")}
                  className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                    labMode === "rl"
                      ? "border-oracle-accent/40 bg-oracle-accent/20 text-oracle-accent"
                      : "border-oracle-border text-oracle-muted hover:text-oracle-text"
                  }`}
                >
                  <span className="inline-flex items-center gap-1">
                    <TestTube2 className="h-3.5 w-3.5" />
                    {language === "es" ? "Agente IA" : "AI agent"}
                  </span>
                </button>
              </div>
            </div>
          </div>

          {labMode === "paper" ? <PaperTradingView /> : <RLTradingView />}
        </div>
      ) : null}
    </SectionWorkspace>
  );
}
