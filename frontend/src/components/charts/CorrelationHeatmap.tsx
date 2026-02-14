"use client";

import { useState } from "react";

interface Props {
  symbols: string[];
  matrix: number[][];
}

function getColor(value: number): string {
  // Red(-1) → White(0) → Green(+1)
  if (value >= 0) {
    const intensity = Math.min(value, 1);
    const r = Math.round(255 - intensity * 200);
    const g = Math.round(255 - intensity * 50);
    const b = Math.round(255 - intensity * 200);
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    const intensity = Math.min(Math.abs(value), 1);
    const r = Math.round(255 - intensity * 50);
    const g = Math.round(255 - intensity * 200);
    const b = Math.round(255 - intensity * 200);
    return `rgb(${r}, ${g}, ${b})`;
  }
}

export default function CorrelationHeatmap({ symbols, matrix }: Props) {
  const [hoveredCell, setHoveredCell] = useState<{ i: number; j: number } | null>(null);

  if (symbols.length < 2 || matrix.length < 2) {
    return (
      <p className="text-oracle-muted text-xs text-center py-4">
        Need at least 2 holdings for correlation analysis
      </p>
    );
  }

  const cellSize = Math.min(40, Math.max(24, 300 / symbols.length));
  const labelWidth = 50;
  const svgWidth = labelWidth + symbols.length * cellSize;
  const svgHeight = labelWidth + symbols.length * cellSize;

  return (
    <div className="relative overflow-x-auto">
      <svg width={svgWidth} height={svgHeight} className="mx-auto">
        {/* Column labels */}
        {symbols.map((sym, j) => (
          <text
            key={`col-${j}`}
            x={labelWidth + j * cellSize + cellSize / 2}
            y={labelWidth - 4}
            textAnchor="middle"
            className="text-[9px] fill-oracle-muted"
          >
            {sym.slice(0, 5)}
          </text>
        ))}

        {/* Row labels + cells */}
        {symbols.map((sym, i) => (
          <g key={`row-${i}`}>
            <text
              x={labelWidth - 4}
              y={labelWidth + i * cellSize + cellSize / 2 + 3}
              textAnchor="end"
              className="text-[9px] fill-oracle-muted"
            >
              {sym.slice(0, 5)}
            </text>
            {matrix[i]?.map((val, j) => (
              <g key={`cell-${i}-${j}`}>
                <rect
                  x={labelWidth + j * cellSize}
                  y={labelWidth + i * cellSize}
                  width={cellSize - 1}
                  height={cellSize - 1}
                  fill={getColor(val)}
                  opacity={0.8}
                  rx={2}
                  className="cursor-pointer"
                  onMouseEnter={() => setHoveredCell({ i, j })}
                  onMouseLeave={() => setHoveredCell(null)}
                />
                {cellSize >= 28 && (
                  <text
                    x={labelWidth + j * cellSize + cellSize / 2 - 0.5}
                    y={labelWidth + i * cellSize + cellSize / 2 + 3}
                    textAnchor="middle"
                    className="text-[8px] font-mono pointer-events-none"
                    fill={Math.abs(val) > 0.5 ? "#fff" : "#94a3b8"}
                  >
                    {val.toFixed(2)}
                  </text>
                )}
              </g>
            ))}
          </g>
        ))}
      </svg>

      {/* Tooltip */}
      {hoveredCell && (
        <div className="absolute top-0 right-0 bg-oracle-panel border border-oracle-border rounded px-2 py-1 text-xs z-10">
          <span className="text-oracle-muted">
            {symbols[hoveredCell.i]} / {symbols[hoveredCell.j]}:
          </span>{" "}
          <span className="text-oracle-text font-mono font-medium">
            {matrix[hoveredCell.i]?.[hoveredCell.j]?.toFixed(4)}
          </span>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-center gap-2 mt-2 text-[9px] text-oracle-muted">
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: getColor(-1) }} />
          <span>-1.0</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: getColor(0) }} />
          <span>0.0</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: getColor(1) }} />
          <span>+1.0</span>
        </div>
      </div>
    </div>
  );
}
