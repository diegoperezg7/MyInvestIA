"use client";

import ChatPanel from "@/components/dashboard/ChatPanel";

export default function ChatView() {
  return (
    <div className="flex h-[calc(100dvh-7.5rem)] min-h-[520px] flex-col lg:h-[calc(100vh-180px)]">
      <ChatPanel expanded />
    </div>
  );
}
