"use client";

import type { ReactNode } from "react";
import type { SectionTabId } from "@/types";

export interface WorkspaceTab {
  id: SectionTabId;
  label: string;
  hint?: string;
}

export default function SectionWorkspace({
  eyebrow,
  title,
  description,
  tabs,
  activeTab,
  onTabChange,
  actions,
  aside,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  tabs: WorkspaceTab[];
  activeTab: SectionTabId;
  onTabChange: (tab: SectionTabId) => void;
  actions?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="space-y-4">
      <section className="oracle-hero-surface rounded-2xl border border-oracle-border p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <span className="rounded-full border border-oracle-accent/30 bg-oracle-accent/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-oracle-accent">
              {eyebrow}
            </span>
            <h2 className="mt-3 text-2xl font-semibold text-oracle-text">{title}</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-oracle-muted">
              {description}
            </p>
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {tabs.map((tab) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                  active
                    ? "border-oracle-accent/40 bg-oracle-accent/20 text-oracle-accent"
                    : "border-oracle-border text-oracle-muted hover:text-oracle-text"
                }`}
                title={tab.hint}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {aside ? <div className="mt-4">{aside}</div> : null}
      </section>

      <div>{children}</div>
    </div>
  );
}
