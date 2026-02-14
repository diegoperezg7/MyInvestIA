"use client";

import SectorHeatmap from "@/components/charts/SectorHeatmap";
import MarketBreadthCard from "@/components/dashboard/MarketBreadthCard";

export default function HeatmapView() {
  return (
    <>
      <div className="mb-4">
        <SectorHeatmap />
      </div>
      <div className="max-w-2xl">
        <MarketBreadthCard />
      </div>
    </>
  );
}
