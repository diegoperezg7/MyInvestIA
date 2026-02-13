"use client";

import ChatPanel from "@/components/dashboard/ChatPanel";

export default function ChatView() {
  return (
    <div className="h-[calc(100vh-180px)] flex flex-col">
      <ChatPanel expanded />
    </div>
  );
}
