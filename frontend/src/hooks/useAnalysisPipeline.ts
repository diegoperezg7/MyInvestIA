import { useState, useCallback, useRef } from "react";

interface PipelineStep {
  id: string;
  name: string;
  description: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  result: Record<string, unknown> | null;
  error: string | null;
  duration_ms: number | null;
}

interface PipelineStatus {
  symbol: string;
  current_step: number;
  total_steps: number;
  steps: PipelineStep[];
  completed: boolean;
  final_analysis: string | null;
  signal: string;
  confidence: number;
}

export function useAnalysisPipeline() {
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const completedRef = useRef(false);

  const run = useCallback((symbol: string) => {
    // Cleanup previous
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setLoading(true);
    setError(null);
    setStatus(null);
    completedRef.current = false;

    const es = new EventSource(`/api/v1/chat/analyze-pipeline/${symbol}`);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data: PipelineStatus = JSON.parse(event.data);
        setStatus(data);

        if (data.completed) {
          completedRef.current = true;
          es.close();
          setLoading(false);
        }
      } catch {
        // Ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
      setLoading(false);
      if (!completedRef.current) {
        setError("Pipeline connection lost");
      }
    };
  }, []);

  const cancel = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setLoading(false);
  }, []);

  return { status, loading, error, run, cancel };
}
