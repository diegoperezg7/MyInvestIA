"use client";

import PortfolioSummary from "@/components/dashboard/PortfolioSummary";
import MarketOverviewCard from "@/components/dashboard/MarketOverviewCard";
import WatchlistCard from "@/components/dashboard/WatchlistCard";
import BreakingNewsFeed from "@/components/dashboard/BreakingNewsFeed";
import PriceChart from "@/components/dashboard/PriceChart";
import QuoteLookup from "@/components/dashboard/QuoteLookup";

export default function OverviewView() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Left + center: 2 columns */}
      <div className="lg:col-span-2 flex flex-col gap-4">
        <PriceChart />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <PortfolioSummary />
          <MarketOverviewCard />
        </div>
      </div>

      {/* Right column: stacked tight */}
      <div className="flex flex-col gap-4">
        <QuoteLookup />
        <WatchlistCard />
        <BreakingNewsFeed defaultCollapsed={false} className="flex-1" />
      </div>
    </div>
  );
}
