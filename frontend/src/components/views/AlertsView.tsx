"use client";

import AlertsPanel from "@/components/dashboard/AlertsPanel";
import NotificationsPanel from "@/components/dashboard/NotificationsPanel";

export default function AlertsView() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2">
        <AlertsPanel />
      </div>
      <NotificationsPanel />
    </div>
  );
}
