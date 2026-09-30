import { Activity, Bell, LogOut, Shield, UserRound } from "lucide-react";
import { useAlertStore } from "../../state/alertStore";
import { alertToRecord } from "../../api/adapters";
import { useAlerts, useBackendHealth } from "../../api/hooks";
import { useAuthStore } from "../../state/authStore";

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

  const { user, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    window.location.pathname = "/login";
  };

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
          <div className="text-[9px] tracking-[0.2em] text-[#06B6D4]">
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

        {/* User Info & Logout */}
        <div className="flex items-center gap-3 border-l border-[#2A3441] pl-4">
          <div className="hidden items-center gap-2 text-[#8B949E] md:flex">
            <UserRound size={14} aria-hidden="true" className="text-[#3B82F6]" />
            <span className="font-semibold text-white">
              {user ? user.name : "OPERATOR"}
            </span>
            <span
              className={`rounded px-1.5 py-0.5 font-mono text-[9px] font-bold ${
                user?.role === "MAIN_ADMIN"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "bg-blue-500/20 text-blue-300 border border-blue-500/40"
              }`}
            >
              {user ? user.role : "CONTROL ROOM"}
            </span>
          </div>

          {user && (
            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center gap-1.5 rounded border border-[#2A3441] bg-[#0A0E14] px-2.5 py-1 text-[11px] font-semibold text-[#8B949E] transition hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-300"
              title="Log out of NetraKon AI"
            >
              <LogOut size={13} />
              <span className="hidden sm:inline">LOGOUT</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

export default TopNav;
