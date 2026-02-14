"use client";

import dynamic from "next/dynamic";

const Dashboard = dynamic(() => import("@/components/Dashboard"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-oracle-primary text-lg font-semibold animate-pulse">
        MyInvest<span style={{ color: "var(--oracle-primary)" }}>IA</span>
      </div>
    </div>
  ),
});

export default function Home() {
  return <Dashboard />;
}
