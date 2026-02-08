import PortfolioSummary from "@/components/dashboard/PortfolioSummary";
import MarketOverviewCard from "@/components/dashboard/MarketOverviewCard";
import WatchlistCard from "@/components/dashboard/WatchlistCard";
import TechnicalAnalysisCard from "@/components/dashboard/TechnicalAnalysisCard";
import PriceChart from "@/components/dashboard/PriceChart";
import QuoteLookup from "@/components/dashboard/QuoteLookup";
import ChatPanel from "@/components/dashboard/ChatPanel";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white">ORACLE</h1>
        <p className="text-oracle-muted mt-1">
          AI Investment Intelligence Dashboard
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <PortfolioSummary />
        <MarketOverviewCard />
        <QuoteLookup />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <PriceChart />
        <TechnicalAnalysisCard />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <WatchlistCard />
        <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
          <h3 className="text-oracle-muted text-sm font-medium mb-3 uppercase tracking-wide">
            Active Alerts
          </h3>
          <p className="text-oracle-muted text-sm">
            No alerts configured. Alerts will appear here once the alert scoring
            system is implemented.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <ChatPanel />
      </div>

      <footer className="mt-auto pt-8 text-center text-oracle-muted text-xs">
        <p>
          ORACLE does not provide financial advice. All information is for
          decision support only.
        </p>
      </footer>
    </main>
  );
}
