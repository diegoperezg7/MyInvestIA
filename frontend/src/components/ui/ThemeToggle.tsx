"use client";

import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";

export default function ThemeToggle({ collapsed = false }: { collapsed?: boolean }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-md text-oracle-muted hover:text-oracle-text hover:bg-oracle-panel-hover transition-colors w-full"
    >
      {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
      {!collapsed && (
        <span>{theme === "dark" ? "Light" : "Dark"}</span>
      )}
    </button>
  );
}
