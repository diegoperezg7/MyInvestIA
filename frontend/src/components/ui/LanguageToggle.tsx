"use client";

import useLanguageStore from "@/stores/useLanguageStore";

export default function LanguageToggle({ collapsed = false }: { collapsed?: boolean }) {
  const { language, toggleLanguage } = useLanguageStore();

  return (
    <button
      onClick={toggleLanguage}
      aria-label={language === "es" ? "Switch to English" : "Cambiar a Espanol"}
      className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md text-oracle-muted hover:text-oracle-text hover:bg-oracle-panel-hover transition-colors w-full"
    >
      <span className="text-sm w-4 text-center">{language === "es" ? "ES" : "EN"}</span>
      {!collapsed && (
        <span>{language === "es" ? "Espanol" : "English"}</span>
      )}
    </button>
  );
}
