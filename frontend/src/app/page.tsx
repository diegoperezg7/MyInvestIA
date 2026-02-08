import PortfolioSummary from "@/components/dashboard/PortfolioSummary";
import MarketOverviewCard from "@/components/dashboard/MarketOverviewCard";
import WatchlistCard from "@/components/dashboard/WatchlistCard";
import TechnicalAnalysisCard from "@/components/dashboard/TechnicalAnalysisCard";
import PriceChart from "@/components/dashboard/PriceChart";
import QuoteLookup from "@/components/dashboard/QuoteLookup";
import ChatPanel from "@/components/dashboard/ChatPanel";
import AlertsPanel from "@/components/dashboard/AlertsPanel";
import MacroPanel from "@/components/dashboard/MacroPanel";

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
        <AlertsPanel />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <MacroPanel />
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
