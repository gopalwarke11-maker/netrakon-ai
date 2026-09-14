import { Activity, Bell, Shield, UserRound } from "lucide-react";
import { useAlertStore } from "../../state/alertStore";
import { alertToRecord } from "../../api/adapters";
import { useAlerts, useBackendHealth } from "../../api/hooks";

function TopNav() {
  const resolvedAlertIds = useAlertStore((state) => state.resolvedAlertIds);
  const connectionStatus = useAlertStore((state) => state.connectionStatus);
  const healthQuery = useBackendHealth();
  const alertsQuery = useAlerts();
  const alerts = alertsQuery.data?.map(alertToRecord) ?? [];
  const activeAlertCount = alerts.filter(
    (alert) =>
      alert.status === "ACTIVE" && !resolvedAlertIds.includes(alert.id),
  ).length;

  return (
    <header className="flex min-h-16 flex-wrap items-center justify-between gap-4 border-b border-[#2A3441] bg-[#141A23] px-4 py-3 sm:px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center border border-[#3B82F6]/50 bg-[#3B82F6]/10 text-[#3B82F6]">
          <Shield size={19} aria-hidden="true" />
        </div>
        <div>
          <div className="text-sm font-bold tracking-[0.18em] text-[#E6EDF3]">
            NETRAKON AI
          </div>
          <div className="text-[9px] tracking-[0.2em] text-[#8B949E]">
            BORDER INTELLIGENCE SYSTEM
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs">
        <div
          className={`flex items-center gap-2 ${healthQuery.isPending ? "text-yellow-300" : healthQuery.isSuccess ? "text-green-400" : "text-orange-300"}`}
        >
          <Activity size={14} aria-hidden="true" />
          <span className="hidden sm:inline">
            {healthQuery.isPending
              ? "BACKEND CHECKING"
              : healthQuery.isSuccess
                ? "BACKEND CONNECTED"
                : "BACKEND OFFLINE"}
          </span>
        </div>
        <div className="hidden items-center gap-2 border-l border-[#2A3441] pl-4 text-cyan-300 sm:flex">
          <span
            className={`h-1.5 w-1.5 rounded-full ${connectionStatus === "CONNECTED" ? "bg-green-300" : connectionStatus === "CONNECTING" ? "bg-yellow-300" : "bg-[#8B949E]"}`}
          />
          ALERT STREAM {connectionStatus}
        </div>
        <div className="flex items-center gap-2 border-l border-[#2A3441] pl-4 text-orange-300">
          <Bell size={14} aria-hidden="true" />
          <span>{String(activeAlertCount).padStart(2, "0")} ACTIVE ALERTS</span>
        </div>
        <div className="hidden items-center gap-2 border-l border-[#2A3441] pl-4 text-[#8B949E] md:flex">
          <UserRound size={14} aria-hidden="true" />
          <span>OPERATOR // CONTROL ROOM 01</span>
        </div>
      </div>
    </header>
  );
}

export default TopNav;
