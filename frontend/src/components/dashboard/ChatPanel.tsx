"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchAPI, postAPI } from "@/lib/api";
import { useBriefing } from "@/hooks/useBriefing";
import type { AIStatus, ChatMessage, ChatResponse } from "@/types";

interface Persona {
  id: string;
  name: string;
  title: string;
  avatar: string;
  style: string;
}

/** Extract [bracketed] suggestion chips from AI text */
function extractSuggestions(text: string): string[] {
  return (text.match(/\[([^\]]+)\]/g) || []).map((s) => s.slice(1, -1));
}

/** Try to extract a stock symbol from user input */
function extractSymbol(text: string): string {
  const match = text.match(/\b([A-Z]{1,5})\b/);
  return match ? match[1] : text.trim().split(" ")[0].toUpperCase();
}

export default function ChatPanel({ expanded = false }: { expanded?: boolean }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [activePersona, setActivePersona] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const briefingInjected = useRef(false);

  const briefing = useBriefing();

  // Fetch AI status and personas on mount
  useEffect(() => {
    fetchAPI<AIStatus>("/api/v1/chat/status")
      .then(setAiStatus)
      .catch(() => setAiStatus({ configured: false, model: "" }));

    fetchAPI<{ personas: Persona[] }>("/api/v1/chat/personas")
      .then((data) => setPersonas(data.personas))
      .catch(() => {});
  }, []);

  // Inject briefing as first assistant message
  useEffect(() => {
    if (briefing.data && !briefingInjected.current && messages.length === 0) {
      briefingInjected.current = true;
      setMessages([{ role: "assistant", content: briefing.data.briefing }]);
      setSuggestions(briefing.data.suggestions);
    }
  }, [briefing.data, messages.length]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, suggestions]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = { role: "user", content: text.trim() };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setSuggestions([]);
    setInput("");
    setLoading(true);

    try {
      if (activePersona) {
        const data = await postAPI<{ analysis: string }>("/api/v1/chat/persona-analyze", {
          symbol: extractSymbol(text),
          persona_id: activePersona,
          question: text.trim(),
        });
        const assistantMsg: ChatMessage = { role: "assistant", content: data.analysis };
        setMessages([...updatedMessages, assistantMsg]);
        setSuggestions(extractSuggestions(data.analysis));
      } else {
        const data = await postAPI<ChatResponse>("/api/v1/chat/", {
          messages: updatedMessages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        });
        const assistantMsg: ChatMessage = { role: "assistant", content: data.response };
        setMessages([...updatedMessages, assistantMsg]);
        setSuggestions(extractSuggestions(data.response));
      }
    } catch (e) {
      setMessages([
        ...updatedMessages,
        {
          role: "assistant",
          content:
            e instanceof Error && e.message.includes("503")
              ? "AI service not configured. Please set MISTRAL_API_KEY in the backend .env file."
              : "Sorry, something went wrong. Please try again.",
        },
      ]);
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = () => sendMessage(input);
  const handleChipClick = (chip: string) => sendMessage(chip);

  const isConfigured = aiStatus?.configured ?? false;
  const currentPersona = personas.find((p) => p.id === activePersona);
  const isBriefingLoading = briefing.loading && messages.length === 0;

  return (
    <div className={`flex flex-col ${expanded ? "flex-1 min-h-0" : "bg-oracle-panel border border-oracle-border rounded-lg p-6"}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          AI Chat
        </h3>
        <div className="flex items-center gap-2">
          {personas.length > 0 && (
            <select
              value={activePersona || ""}
              onChange={(e) => setActivePersona(e.target.value || null)}
              className="bg-oracle-bg border border-oracle-border rounded px-2 py-0.5 text-xs text-oracle-text"
            >
              <option value="">Default AI</option>
              {personas.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.avatar} {p.name}
                </option>
              ))}
            </select>
          )}
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
      </div>

      {currentPersona && (
        <div className="bg-oracle-bg rounded px-3 py-1.5 mb-3 text-xs text-oracle-muted">
          Chatting as <span className="text-oracle-text font-medium">{currentPersona.name}</span>
          {" - "}{currentPersona.style}
        </div>
      )}

      <div
        ref={scrollRef}
        className={`flex-1 overflow-y-auto space-y-3 mb-3 min-h-0 ${
          expanded ? "" : "min-h-[200px] max-h-[400px]"
        }`}
      >
        {/* Briefing loading state */}
        {isBriefingLoading && (
          <div className="flex justify-start">
            <div className="bg-oracle-bg text-oracle-muted border border-oracle-border rounded-lg px-4 py-3 text-sm flex items-center gap-2">
              <span className="inline-block w-2 h-2 bg-oracle-accent rounded-full animate-pulse" />
              Scanning your portfolio and market news...
            </div>
          </div>
        )}

        {/* Empty state only if no briefing loading */}
        {messages.length === 0 && !isBriefingLoading && !briefing.data && (
          <div className="text-oracle-muted text-sm text-center py-8">
            <p className="mb-2">Ask MyInvestIA about markets, assets, or your portfolio.</p>
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
              className={`rounded-lg px-4 py-2.5 text-sm ${
                msg.role === "user"
                  ? "max-w-[75%] bg-oracle-accent text-white"
                  : `${expanded ? "max-w-[90%]" : "max-w-[85%]"} bg-oracle-bg text-oracle-text border border-oracle-border`
              }`}
            >
              {msg.role === "user" ? (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              ) : (
                <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-pre:bg-black/30 prose-pre:border prose-pre:border-oracle-border prose-pre:rounded prose-code:text-oracle-accent prose-code:before:content-none prose-code:after:content-none prose-strong:text-oracle-text prose-a:text-oracle-accent prose-table:border-collapse prose-th:border prose-th:border-oracle-border prose-th:bg-oracle-panel prose-th:px-3 prose-th:py-1.5 prose-th:text-left prose-th:text-oracle-text prose-th:font-semibold prose-td:border prose-td:border-oracle-border prose-td:px-3 prose-td:py-1.5 prose-hr:border-oracle-border">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-oracle-bg text-oracle-muted border border-oracle-border rounded-lg px-3 py-2 text-sm">
              {currentPersona ? `${currentPersona.name} is thinking...` : "Thinking..."}
            </div>
          </div>
        )}
      </div>

      {/* Suggestion chips */}
      {suggestions.length > 0 && !loading && (
        <div className="flex flex-wrap gap-2 mb-3">
          {suggestions.map((chip) => (
            <button
              key={chip}
              onClick={() => handleChipClick(chip)}
              className="text-xs px-3 py-1.5 rounded-full border border-oracle-accent/40 text-oracle-accent bg-oracle-accent/5 hover:bg-oracle-accent/15 hover:border-oracle-accent/60 transition-colors cursor-pointer"
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder={
            isConfigured
              ? currentPersona
                ? `Ask ${currentPersona.name} about markets...`
                : "Ask about markets, assets, or analysis..."
              : "AI not configured - set MISTRAL_API_KEY"
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
