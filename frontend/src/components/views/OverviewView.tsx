"use client";

import PortfolioSummary from "@/components/dashboard/PortfolioSummary";
import MarketOverviewCard from "@/components/dashboard/MarketOverviewCard";
import WatchlistCard from "@/components/dashboard/WatchlistCard";
import BreakingNewsFeed from "@/components/dashboard/BreakingNewsFeed";
import PriceChart from "@/components/dashboard/PriceChart";
import QuoteLookup from "@/components/dashboard/QuoteLookup";

export default function OverviewView() {
  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <div className="lg:col-span-2">
          <PriceChart />
        </div>
        <QuoteLookup />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <PortfolioSummary />
        <MarketOverviewCard />
        <div className="flex flex-col gap-4">
          <WatchlistCard />
          <BreakingNewsFeed defaultCollapsed={false} className="flex-1" />
        </div>
      </div>
    </>
  );
}
