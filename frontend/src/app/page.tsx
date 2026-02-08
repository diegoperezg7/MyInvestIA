export default function Home() {
  return (
    <main className="flex min-h-screen flex-col p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white">ORACLE</h1>
        <p className="text-oracle-muted mt-1">
          AI Investment Intelligence Dashboard
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <DashboardCard title="Portfolio Value" value="--" />
        <DashboardCard title="Daily PnL" value="--" />
        <DashboardCard title="Market Sentiment" value="--" />
        <DashboardCard title="Active Alerts" value="0" />
        <DashboardCard title="Top Gainer" value="--" />
        <DashboardCard title="Top Loser" value="--" />
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

function DashboardCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-4">
      <h3 className="text-oracle-muted text-sm font-medium">{title}</h3>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}
