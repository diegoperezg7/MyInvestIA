"use client";

import { Bell, BriefcaseBusiness, Home, Menu, Sparkles } from "lucide-react";

import { useView } from "@/contexts/ViewContext";
import { getSectionLabel } from "@/lib/shell";
import useLanguageStore from "@/stores/useLanguageStore";

const PRIMARY_MOBILE_SECTIONS = [
  { id: "home", icon: Home },
  { id: "priorities", icon: Sparkles },
  { id: "portfolio", icon: BriefcaseBusiness },
  { id: "assistant", icon: Bell },
] as const;

export default function MobileBottomNav() {
  const { activeSection, focusView, setActiveSection, setSidebarMobileOpen } = useView();
  const language = useLanguageStore((state) => state.language);

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-oracle-border bg-oracle-panel/95 px-2 pb-[calc(env(safe-area-inset-bottom,0px)+0.5rem)] pt-2 backdrop-blur lg:hidden">
      <div className="grid grid-cols-5 gap-1">
        {PRIMARY_MOBILE_SECTIONS.map((item) => {
          const Icon = item.icon;
          const active = focusView === null && activeSection === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={`flex flex-col items-center gap-1 rounded-xl px-2 py-2 text-[11px] transition-colors ${
                active
                  ? "bg-oracle-accent/15 text-oracle-accent"
                  : "text-oracle-muted hover:text-oracle-text"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{getSectionLabel(item.id, language)}</span>
            </button>
          );
        })}
        <button
          onClick={() => setSidebarMobileOpen(true)}
          className="flex flex-col items-center gap-1 rounded-xl px-2 py-2 text-[11px] text-oracle-muted transition-colors hover:text-oracle-text"
        >
          <Menu className="h-4 w-4" />
          <span>{language === "es" ? "Más" : "More"}</span>
        </button>
      </div>
    </nav>
  );
}
