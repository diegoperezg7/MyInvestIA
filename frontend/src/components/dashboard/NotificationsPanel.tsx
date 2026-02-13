"use client";

import { useState, useEffect } from "react";
import { fetchAPI, postAPI } from "@/lib/api";
import type { NotificationStatus, NotificationResponse } from "@/types";

export default function NotificationsPanel() {
  const [status, setStatus] = useState<NotificationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState("");
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetchAPI<NotificationStatus>(
          "/api/v1/notifications/status"
        );
        if (!cancelled) setStatus(res);
      } catch {
        if (!cancelled)
          setStatus({ configured: false, bot_name: null, bot_username: null, chat_id: null });
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleTest() {
    setSending(true);
    setFeedback(null);
    try {
      const res = await postAPI<NotificationResponse>(
        "/api/v1/notifications/test",
        {}
      );
      setFeedback({
        type: res.success ? "success" : "error",
        text: res.message,
      });
    } catch (e) {
      setFeedback({
        type: "error",
        text: e instanceof Error ? e.message : "Failed to send test",
      });
    } finally {
      setSending(false);
    }
  }

  async function handleSend() {
    if (!message.trim()) return;
    setSending(true);
    setFeedback(null);
    try {
      const res = await postAPI<NotificationResponse>(
        "/api/v1/notifications/send",
        { message: message.trim() }
      );
      setFeedback({
        type: res.success ? "success" : "error",
        text: res.message,
      });
      if (res.success) setMessage("");
    } catch (e) {
      setFeedback({
        type: "error",
        text: e instanceof Error ? e.message : "Failed to send",
      });
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="bg-oracle-panel border border-oracle-border rounded-lg p-6">
      <h3 className="text-oracle-muted text-sm font-medium uppercase tracking-wide mb-3">
        Telegram Notifications
      </h3>

      {loading && (
        <p className="text-oracle-muted text-sm">Checking status...</p>
      )}

      {!loading && status && (
        <>
          {/* Status indicator */}
          <div className="flex items-center gap-2 mb-4">
            <span
              className={`w-2 h-2 rounded-full ${
                status.configured ? "bg-oracle-green" : "bg-oracle-red"
              }`}
            />
            <span className="text-sm text-oracle-text">
              {status.configured
                ? `Connected${status.bot_name ? ` — ${status.bot_name}` : ""}`
                : "Not configured"}
            </span>
            {status.bot_username && (
              <span className="text-xs text-oracle-muted">
                @{status.bot_username}
              </span>
            )}
          </div>

          {status.configured ? (
            <>
              {/* Test button */}
              <button
                onClick={handleTest}
                disabled={sending}
                className="mb-4 px-3 py-1.5 text-sm bg-oracle-accent/20 text-oracle-accent border border-oracle-accent/30 rounded hover:bg-oracle-accent/30 disabled:opacity-50"
              >
                {sending ? "Sending..." : "Send Test"}
              </button>

              {/* Custom message */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  placeholder="Send a custom message..."
                  className="flex-1 bg-oracle-bg border border-oracle-border rounded px-3 py-1.5 text-sm text-oracle-text placeholder:text-oracle-muted focus:outline-none focus:border-oracle-accent"
                />
                <button
                  onClick={handleSend}
                  disabled={sending || !message.trim()}
                  className="px-3 py-1.5 text-sm bg-oracle-green/20 text-oracle-green border border-oracle-green/30 rounded hover:bg-oracle-green/30 disabled:opacity-50"
                >
                  Send
                </button>
              </div>
            </>
          ) : (
            <p className="text-oracle-muted text-xs">
              Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file to
              enable notifications.
            </p>
          )}

          {/* Feedback */}
          {feedback && (
            <p
              className={`mt-3 text-xs ${
                feedback.type === "success"
                  ? "text-oracle-green"
                  : "text-oracle-red"
              }`}
            >
              {feedback.text}
            </p>
          )}
        </>
      )}
    </div>
  );
}
