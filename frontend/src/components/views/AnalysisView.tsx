"use client";

import TechnicalAnalysisCard from "@/components/dashboard/TechnicalAnalysisCard";
import EnhancedSentimentCard from "@/components/dashboard/EnhancedSentimentCard";
import AnalysisPipeline from "@/components/analysis/AnalysisPipeline";
import SignalSummaryCard from "@/components/analysis/SignalSummaryCard";
import FundamentalsCard from "@/components/dashboard/FundamentalsCard";

export default function AnalysisView() {
  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <TechnicalAnalysisCard />
        <FundamentalsCard />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <EnhancedSentimentCard />
        <SignalSummaryCard />
      </div>

      <div className="grid grid-cols-1 gap-4">
        <AnalysisPipeline />
      </div>
    </>
  );
}
