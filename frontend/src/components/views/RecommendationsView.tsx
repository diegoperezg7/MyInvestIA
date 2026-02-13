"use client";

import RecommendationsPanel from "@/components/dashboard/RecommendationsPanel";
import BreakingNewsFeed from "@/components/dashboard/BreakingNewsFeed";

export default function RecommendationsView() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
      <div className="lg:col-span-2">
        <RecommendationsPanel />
      </div>
      <div className="lg:sticky lg:top-4">
        <BreakingNewsFeed defaultCollapsed={false} />
      </div>
    </div>
  );
}
