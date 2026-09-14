import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, Search, ShieldAlert } from "lucide-react";
import { useAlertStore } from "../../state/alertStore";
import { alertToRecord } from "../../api/adapters";
import { getRiskAssessment, updateAlert } from "../../api/alerts";
import { useAlerts, useCameras } from "../../api/hooks";
import type { AlertRecord, RiskLevel } from "../../data/mockData";

const riskColors: Record<RiskLevel, string> = {
  LOW: "text-green-300 border-green-500/40",
  MEDIUM: "text-yellow-300 border-yellow-500/40",
  HIGH: "text-orange-300 border-orange-500/40",
  CRITICAL: "text-red-300 border-red-500/40",
};

function AlertCenter() {
  const [query, setQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<"ALL" | RiskLevel>("ALL");
  const [cameraFilter, setCameraFilter] = useState("ALL");
  const [sectorFilter, setSectorFilter] = useState("ALL");
  const [alertView, setAlertView] = useState<"ACTIVE" | "RESOLVED">("ACTIVE");
  const [selectedAlert, setSelectedAlert] = useState<AlertRecord>();
  const resolvedAlertIds = useAlertStore((state) => state.resolvedAlertIds);
  const resolveAlert = useAlertStore((state) => state.resolveAlert);
  const queryClient = useQueryClient();
  const alertsQuery = useAlerts();
  const camerasQuery = useCameras();
  const alerts = useMemo(
    () => alertsQuery.data?.map(alertToRecord) ?? [],
    [alertsQuery.data],
  );
  const cameraOptions = useMemo(
    () => (camerasQuery.data ?? []).map((camera) => camera.id).sort(),
    [camerasQuery.data],
  );
  const sectorOptions = useMemo(
    () => [...new Set(alerts.map((alert) => alert.sector))].sort(),
    [alerts],
  );

  const visibleAlerts = useMemo(
    () =>
      alerts.filter((alert) => {
        const status = resolvedAlertIds.includes(alert.id)
          ? "RESOLVED"
          : alert.status;
        const matchesQuery = `${alert.id} ${alert.trackId} ${alert.objectType}`
          .toLowerCase()
          .includes(query.toLowerCase());
        return (
          matchesQuery &&
          (riskFilter === "ALL" || alert.risk === riskFilter) &&
          (cameraFilter === "ALL" || alert.cameraId === cameraFilter) &&
          (sectorFilter === "ALL" || alert.sector === sectorFilter) &&
          status === alertView
        );
      }),
    [
      alertView,
      cameraFilter,
      query,
      resolvedAlertIds,
      riskFilter,
      sectorFilter,
      alerts,
    ],
  );

  const displayedAlert =
    selectedAlert && alerts.some((alert) => alert.id === selectedAlert.id)
      ? selectedAlert
      : visibleAlerts[0];
  const riskQuery = useQuery({
    queryKey: ["risk", displayedAlert?.eventId],
    queryFn: () => getRiskAssessment(displayedAlert!.eventId!),
    enabled: Boolean(displayedAlert?.eventId),
    retry: false,
  });

  const activeCount = alerts.filter(
    (alert) =>
      alert.status === "ACTIVE" && !resolvedAlertIds.includes(alert.id),
  ).length;

  const handleResolve = async (alertId: string) => {
    resolveAlert(alertId);
    if (alertsQuery.data) {
      try {
        await updateAlert(alertId, { status: "RESOLVED" });
        await queryClient.invalidateQueries({ queryKey: ["alerts"] });
      } catch {
        // Keep the local resolution visible if the server becomes unavailable.
      }
    }
  };

  return (
    <section className="overflow-hidden border border-[#2A3441] bg-[#141A23]">
      <div className="flex items-center justify-between border-b border-[#2A3441] px-4 py-3">
        <div className="flex items-center gap-2">
          <ShieldAlert size={15} className="text-red-400" aria-hidden="true" />
          <h2 className="text-xs font-semibold tracking-[0.15em]">
            ALERT CENTER
          </h2>
        </div>
        <span className="text-[10px] text-[#8B949E]">
          {activeCount} ACTIVE //{" "}
          {alertsQuery.isError
            ? "BACKEND UNAVAILABLE"
            : alertsQuery.isLoading
              ? "LOADING"
              : "LIVE BACKEND"}
        </span>
      </div>
      {alertsQuery.isLoading && (
        <p className="border-b border-[#2A3441] px-4 py-2 text-[10px] text-[#8B949E]">
          LOADING ALERTS...
        </p>
      )}
      {alertsQuery.isError && (
        <div className="flex items-center justify-between border-b border-orange-400/40 bg-orange-400/5 px-4 py-2 text-[10px] text-orange-200">
          <span>BACKEND UNAVAILABLE // NO ALERT HISTORY</span>
          <button
            type="button"
            onClick={() => void alertsQuery.refetch()}
            className="font-bold underline"
          >
            RETRY
          </button>
        </div>
      )}
      <div className="flex border-b border-[#2A3441] px-3 pt-3">
        {(["ACTIVE", "RESOLVED"] as const).map((view) => (
          <button
            key={view}
            type="button"
            onClick={() => setAlertView(view)}
            className={`border-b-2 px-3 pb-2 text-[10px] font-bold tracking-wider ${alertView === view ? "border-[#3B82F6] text-[#E6EDF3]" : "border-transparent text-[#8B949E]"}`}
            aria-pressed={alertView === view}
          >
            {view} (
            {view === "ACTIVE"
              ? activeCount
              : alerts.filter(
                  (alert) =>
                    alert.status === "RESOLVED" ||
                    resolvedAlertIds.includes(alert.id),
                ).length}
            )
          </button>
        ))}
      </div>
      <div className="grid gap-3 border-b border-[#2A3441] p-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="relative sm:col-span-2 lg:col-span-1">
          <Search
            size={13}
            className="absolute left-2.5 top-2.5 text-[#8B949E]"
            aria-hidden="true"
          />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search alerts"
            className="h-8 w-full border border-[#2A3441] bg-[#0A0E14] pl-8 pr-2 text-xs text-[#E6EDF3] outline-none placeholder:text-[#8B949E] focus:border-[#3B82F6]"
          />
        </label>
        <select
          value={riskFilter}
          onChange={(event) =>
            setRiskFilter(event.target.value as "ALL" | RiskLevel)
          }
          className="h-8 border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3] outline-none"
        >
          <option value="ALL">ALL RISKS</option>
          <option value="LOW">LOW</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="HIGH">HIGH</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
        <select
          value={cameraFilter}
          onChange={(event) => setCameraFilter(event.target.value)}
          className="h-8 border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3] outline-none"
        >
          <option value="ALL">ALL CAMERAS</option>
          {cameraOptions.map((camera) => (
            <option key={camera}>{camera}</option>
          ))}
        </select>
        <select
          value={sectorFilter}
          onChange={(event) => setSectorFilter(event.target.value)}
          className="h-8 border border-[#2A3441] bg-[#0A0E14] px-2 text-xs text-[#E6EDF3] outline-none"
        >
          <option value="ALL">ALL SECTORS</option>
          {sectorOptions.map((sector) => (
            <option key={sector}>{sector}</option>
          ))}
        </select>
      </div>
      <div className="grid lg:grid-cols-[1.2fr_1fr]">
        <div className="divide-y divide-[#2A3441]">
          {visibleAlerts.length === 0 && (
            <p className="p-5 text-xs text-[#8B949E]">
              No {alertView.toLowerCase()} alerts match the selected filters.
            </p>
          )}
          {visibleAlerts.map((alert) => (
            <button
              key={alert.id}
              type="button"
              onClick={() => setSelectedAlert(alert)}
              className={`block w-full p-3 text-left transition hover:bg-[#0A0E14] ${displayedAlert?.id === alert.id ? "border-l-2 border-[#3B82F6] bg-[#0A0E14]" : "border-l-2 border-transparent"}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 text-xs font-bold">
                  <AlertTriangle
                    size={13}
                    className={riskColors[alert.risk].split(" ")[0]}
                    aria-hidden="true"
                  />
                  {alert.objectType} ALERT
                </span>
                <span
                  className={`border px-1.5 py-0.5 text-[9px] font-bold ${riskColors[alert.risk]}`}
                >
                  {alert.risk}
                </span>
              </div>
              <div className="mt-2 flex justify-between text-[10px] text-[#8B949E]">
                <span>
                  {alert.cameraId} // {alert.sector}
                </span>
                <span>{alert.timestamp}</span>
              </div>
              <div className="mt-2 text-[9px] text-[#8B949E]">
                STATUS:{" "}
                {resolvedAlertIds.includes(alert.id) ||
                alert.status === "RESOLVED"
                  ? "RESOLVED"
                  : "ACTIVE"}
              </div>
            </button>
          ))}
        </div>
        {displayedAlert && (
          <div className="border-t border-[#2A3441] p-4 lg:border-l lg:border-t-0">
            <div className="flex items-center justify-between">
              <span className="text-[10px] tracking-[0.15em] text-[#8B949E]">
                ALERT DETAILS
              </span>
              <span
                className={`border px-1.5 py-0.5 text-[9px] font-bold ${riskColors[displayedAlert.risk]}`}
              >
                {displayedAlert.risk}
              </span>
            </div>
            <p className="mt-2 text-[9px] font-bold tracking-wider text-[#8B949E]">
              STATUS:{" "}
              {resolvedAlertIds.includes(displayedAlert.id) ||
              displayedAlert.status === "RESOLVED"
                ? "RESOLVED"
                : "ACTIVE"}
            </p>
            <h3 className="mt-3 text-sm font-bold">
              {displayedAlert.objectType} DETECTED
            </h3>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-[10px]">
              <div>
                <dt className="text-[#8B949E]">TRACK</dt>
                <dd>{displayedAlert.trackId}</dd>
              </div>
              <div>
                <dt className="text-[#8B949E]">CONFIDENCE</dt>
                <dd className="text-cyan-300">{displayedAlert.confidence}%</dd>
              </div>
              <div>
                <dt className="text-[#8B949E]">CAMERA</dt>
                <dd>{displayedAlert.cameraId}</dd>
              </div>
              <div>
                <dt className="text-[#8B949E]">TIME</dt>
                <dd>{displayedAlert.timestamp}</dd>
              </div>
            </dl>
            <p className="mt-4 border-l-2 border-orange-400/60 pl-3 text-xs leading-relaxed text-[#8B949E]">
              {displayedAlert.description}
            </p>
            {riskQuery.data && (
              <div className="mt-4 border border-[#2A3441] bg-[#0A0E14] p-3 text-[10px]">
                <div className="flex items-center justify-between font-bold">
                  <span>RISK ASSESSMENT</span>
                  <span className="text-orange-300">
                    {riskQuery.data.risk_score} / {riskQuery.data.risk_level}
                  </span>
                </div>
                <p className="mt-2 text-[#8B949E]">FACTORS</p>
                <ul className="mt-1 space-y-1 text-[#8B949E]">
                  {riskQuery.data.factors.map((factor) => (
                    <li key={factor.factor}>
                      {factor.factor}: {factor.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {displayedAlert.status === "ACTIVE" &&
              !resolvedAlertIds.includes(displayedAlert.id) && (
                <button
                  type="button"
                  onClick={() => void handleResolve(displayedAlert.id)}
                  className="mt-5 flex items-center gap-2 border border-green-500/40 px-3 py-2 text-[10px] font-bold text-green-300 hover:bg-green-500/10"
                >
                  <Check size={13} aria-hidden="true" /> MARK RESOLVED
                </button>
              )}
          </div>
        )}
      </div>
    </section>
  );
}

export default AlertCenter;
