"use client";

import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api";

interface Preset {
  id: string;
  name: string;
  description: string;
}

interface Props {
  onSelect: (presetId: string) => void;
}

export default function PresetStrategies({ onSelect }: Props) {
  const [presets, setPresets] = useState<Preset[]>([]);

  useEffect(() => {
    fetchAPI<{ presets: Preset[] }>("/api/v1/screener/presets")
      .then((data) => setPresets(data.presets))
      .catch(() => {});
  }, []);

  if (presets.length === 0) return null;

  return (
    <div className="mt-4 pt-3 border-t border-oracle-border">
      <h4 className="text-oracle-muted text-xs font-medium uppercase mb-2">Presets</h4>
      <div className="space-y-1">
        {presets.map((p) => (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className="w-full text-left px-2 py-1.5 rounded hover:bg-oracle-bg transition-colors"
          >
            <span className="text-xs text-oracle-text">{p.name}</span>
            <p className="text-[10px] text-oracle-muted">{p.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
