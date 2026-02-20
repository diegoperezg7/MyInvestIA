"use client";

import dynamic from "next/dynamic";
import { useAuth } from "@/contexts/AuthContext";
import LoginPage from "@/components/auth/LoginPage";

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
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-oracle-primary text-lg font-semibold animate-pulse">
          MyInvest<span style={{ color: "var(--oracle-primary)" }}>IA</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return <Dashboard />;
}
