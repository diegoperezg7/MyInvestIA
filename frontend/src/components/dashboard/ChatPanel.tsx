"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchAPI, postAPI, postStream } from "@/lib/api";
import { useBriefing } from "@/hooks/useBriefing";
import type { AIStatus, ChatMessage } from "@/types";

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
  const [streamingContent, setStreamingContent] = useState("");
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [activePersona, setActivePersona] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const briefingInjected = useRef(false);
  const streamAccumulator = useRef("");

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

    if (activePersona) {
      try {
        const data = await postAPI<{ analysis: string }>("/api/v1/chat/persona-analyze", {
          symbol: extractSymbol(text),
          persona_id: activePersona,
          question: text.trim(),
        });
        const assistantMsg: ChatMessage = { role: "assistant", content: data.analysis };
        setMessages([...updatedMessages, assistantMsg]);
        setSuggestions(extractSuggestions(data.analysis));
      } catch {
        setMessages([...updatedMessages, { role: "assistant", content: "Sorry, something went wrong. Please try again." }]);
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
      return;
    }

    // Streaming chat
    streamAccumulator.current = "";
    setStreamingContent("");

    await postStream(
      "/api/v1/chat/",
      { messages: updatedMessages.map((m) => ({ role: m.role, content: m.content })) },
      (token) => {
        streamAccumulator.current += token;
        setStreamingContent(streamAccumulator.current);
      },
      () => {
        const finalContent = streamAccumulator.current;
        streamAccumulator.current = "";
        setStreamingContent("");
        setMessages([...updatedMessages, { role: "assistant", content: finalContent }]);
        setSuggestions(extractSuggestions(finalContent));
        setLoading(false);
      },
      () => {
        setStreamingContent("");
        setMessages([...updatedMessages, { role: "assistant", content: "Sorry, something went wrong. Please try again." }]);
        setSuggestions([]);
        setLoading(false);
      },
    );
  };

  const handleSend = () => sendMessage(input);
  const handleChipClick = (chip: string) => sendMessage(chip);

  const startNewConversation = () => {
    setMessages([]);
    setSuggestions([]);
    setActivePersona(null);
    briefingInjected.current = false;
    if (briefing.data) {
      setMessages([{ role: "assistant", content: briefing.data.briefing }]);
      setSuggestions(briefing.data.suggestions);
    }
  };

  const hasConversation = messages.length > 0;

  const isConfigured = aiStatus?.configured ?? false;
  const currentPersona = personas.find((p) => p.id === activePersona);
  const isBriefingLoading = briefing.loading && messages.length === 0;
  const shellClass = expanded
    ? "flex flex-1 min-h-0 flex-col rounded-2xl border border-oracle-border bg-oracle-panel p-3 shadow-sm sm:p-4"
    : "flex flex-col rounded-lg border border-oracle-border bg-oracle-panel p-6";
  const assistantBubbleClass = expanded
    ? "max-w-[96%] border border-oracle-border bg-oracle-panel text-oracle-text shadow-sm sm:max-w-[92%]"
    : "max-w-[85%] border border-oracle-border bg-oracle-bg/70 text-oracle-text";
  const markdownClass =
    "oracle-prose prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-code:before:content-none prose-code:after:content-none";

  return (
    <div className={shellClass}>
      <div className="mb-4 flex flex-col gap-3 border-b border-oracle-border pb-3 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide">
          AI Chat
        </h3>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
          {hasConversation && (
            <button
              onClick={startNewConversation}
              className="rounded border border-oracle-border px-2 py-1 text-xs text-oracle-muted transition-colors hover:border-oracle-accent/50 hover:text-oracle-text"
              title="Start new conversation"
            >
              New Chat
            </button>
          )}
          {personas.length > 0 && (
            <select
              value={activePersona || ""}
              onChange={(e) => setActivePersona(e.target.value || null)}
              className="min-w-0 flex-1 rounded border border-oracle-border bg-oracle-bg px-2 py-1 text-xs text-oracle-text sm:min-w-[180px] sm:flex-none"
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
            className={`shrink-0 rounded px-2 py-1 text-xs ${
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
        <div className="mb-3 rounded-xl border border-oracle-border bg-oracle-bg/60 px-3 py-2 text-xs text-oracle-muted">
          Chatting as <span className="text-oracle-text font-medium">{currentPersona.name}</span>
          {" - "}{currentPersona.style}
        </div>
      )}

      <div
        ref={scrollRef}
        className={`mb-3 flex-1 space-y-3 overflow-y-auto rounded-2xl border border-oracle-border bg-oracle-bg/35 p-3 min-h-0 sm:p-4 ${
          expanded ? "" : "min-h-[200px] max-h-[400px]"
        }`}
      >
        {/* Briefing loading state */}
        {isBriefingLoading && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-lg border border-oracle-border bg-oracle-panel px-4 py-3 text-sm text-oracle-muted">
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
                  ? "max-w-[88%] bg-oracle-accent text-white sm:max-w-[75%]"
                  : assistantBubbleClass
              }`}
            >
              {msg.role === "user" ? (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              ) : (
                <div className={markdownClass}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && streamingContent && (
          <div className="flex justify-start">
            <div className={`${assistantBubbleClass} rounded-lg px-4 py-2.5 text-sm`}>
              <div className={markdownClass}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingContent}</ReactMarkdown>
              </div>
              <span className="inline-block w-[2px] h-[1em] bg-oracle-accent align-middle ml-0.5 animate-pulse" />
            </div>
          </div>
        )}

        {loading && !streamingContent && (
          <div className="flex justify-start">
            <div className="flex items-center gap-1.5 rounded-lg border border-oracle-border bg-oracle-panel px-3 py-2 text-sm text-oracle-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-oracle-accent/60 animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-oracle-accent/60 animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-oracle-accent/60 animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}
      </div>

      {/* Suggestion chips */}
      {suggestions.length > 0 && !loading && (
        <div className="mb-3 flex flex-wrap gap-2">
          {suggestions.map((chip) => (
            <button
              key={chip}
              onClick={() => handleChipClick(chip)}
              className="cursor-pointer rounded-full border border-oracle-accent/40 bg-oracle-accent/5 px-3 py-1.5 text-xs text-oracle-accent transition-colors hover:border-oracle-accent/60 hover:bg-oracle-accent/15"
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      <div className="mt-auto flex flex-col gap-2 sm:flex-row">
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
              : "AI not configured - set GROQ_API_KEY"
          }
          disabled={!isConfigured && messages.length === 0}
          className="flex-1 rounded-xl border border-oracle-border bg-oracle-bg px-3 py-2 text-sm text-oracle-text placeholder:text-oracle-muted focus:border-oracle-accent focus:outline-none disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="w-full rounded-xl bg-oracle-accent px-4 py-2 text-sm text-white transition-colors hover:bg-oracle-accent/80 disabled:opacity-50 sm:w-auto"
        >
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
