"use client";

import { Menu, Search } from "lucide-react";
import { useView } from "@/contexts/ViewContext";

export default function MobileTopBar() {
  const { setSidebarMobileOpen, setCommandBarOpen } = useView();

  return (
    <div className="flex items-center justify-between h-12 px-4 border-b border-oracle-border bg-oracle-panel lg:hidden">
      <button
        onClick={() => setSidebarMobileOpen(true)}
        className="text-oracle-muted hover:text-oracle-text p-1"
        aria-label="Open menu"
      >
        <Menu size={20} />
      </button>

      <span
        className="font-bold text-sm tracking-wider"
        style={{ color: "var(--oracle-primary)" }}
      >
        MyInvestIA
      </span>

      <button
        onClick={() => setCommandBarOpen(true)}
        className="text-oracle-muted hover:text-oracle-text p-1"
        aria-label="Search"
      >
        <Search size={20} />
      </button>
    </div>
  );
}
