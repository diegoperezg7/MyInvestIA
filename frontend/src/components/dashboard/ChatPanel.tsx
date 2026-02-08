"use client";

import { useEffect, useRef, useState } from "react";
import { fetchAPI, postAPI } from "@/lib/api";
import type { AIStatus, ChatMessage, ChatResponse } from "@/types";

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchAPI<AIStatus>("/api/v1/chat/status")
      .then(setAiStatus)
      .catch(() => setAiStatus({ configured: false, model: "" }));
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: ChatMessage = { role: "user", content: input.trim() };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setLoading(true);

    try {
      const data = await postAPI<ChatResponse>("/api/v1/chat/", {
        messages: updatedMessages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      });
      setMessages([
        ...updatedMessages,
        { role: "assistant", content: data.response },
      ]);
    } catch (e) {
      setMessages([
        ...updatedMessages,
        {
          role: "assistant",
          content:
            e instanceof Error && e.message.includes("503")
              ? "AI service not configured. Please set ANTHROPIC_API_KEY in the backend .env file."
              : "Sorry, something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const isConfigured = aiStatus?.configured ?? false;

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          AI Chat
        </h3>
        <span
          className={`text-xs px-2 py-0.5 rounded ${
            isConfigured
              ? "bg-oracle-green/10 text-oracle-green border border-oracle-green/30"
              : "bg-oracle-red/10 text-oracle-red border border-oracle-red/30"
          }`}
        >
          {isConfigured ? "Connected" : "Not configured"}
        </span>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 min-h-[200px] max-h-[400px] overflow-y-auto space-y-3 mb-3"
      >
        {messages.length === 0 && (
          <div className="text-oracle-muted text-sm text-center py-8">
            <p className="mb-2">Ask ORACLE about markets, assets, or your portfolio.</p>
            <div className="space-y-1 text-xs">
              <p className="text-oracle-muted/70">Try: &quot;What do you think about AAPL?&quot;</p>
              <p className="text-oracle-muted/70">Try: &quot;Explain RSI and how to use it&quot;</p>
              <p className="text-oracle-muted/70">Try: &quot;Compare NVDA vs AMD&quot;</p>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-oracle-accent text-white"
                  : "bg-oracle-bg text-oracle-text border border-oracle-border"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-oracle-bg text-oracle-muted border border-oracle-border rounded-lg px-3 py-2 text-sm">
              Thinking...
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder={
            isConfigured
              ? "Ask about markets, assets, or analysis..."
              : "AI not configured - set ANTHROPIC_API_KEY"
          }
          disabled={!isConfigured && messages.length === 0}
          className="flex-1 bg-oracle-bg border border-oracle-border rounded px-3 py-2 text-sm text-oracle-text placeholder:text-oracle-muted focus:outline-none focus:border-oracle-accent disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="bg-oracle-accent text-white text-sm px-4 py-2 rounded hover:bg-oracle-accent/80 disabled:opacity-50 transition-colors"
        >
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
