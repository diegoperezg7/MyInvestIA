"use client";

import CommoditiesPanel from "@/components/dashboard/CommoditiesPanel";

export default function CommoditiesView() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="lg:col-span-2">
        <CommoditiesPanel />
      </div>
    </div>
  );
}
