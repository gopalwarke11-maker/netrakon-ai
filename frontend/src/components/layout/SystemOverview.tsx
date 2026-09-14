import {
  Activity,
  AlertTriangle,
  Camera,
  Crosshair,
  ShieldCheck,
} from "lucide-react";
import { alertToRecord } from "../../api/adapters";
import {
  useAlerts,
  useBackendHealth,
  useCameras,
  useCameraProcessingStatuses,
  useCameraRuntimeSummaries,
} from "../../api/hooks";
import { useAlertStore } from "../../state/alertStore";

function SystemOverview() {
  const healthQuery = useBackendHealth();
  const camerasQuery = useCameras();
  const alertsQuery = useAlerts();
  const summariesQuery = useCameraRuntimeSummaries();
  const cameras = camerasQuery.data ?? [];
  const processingQueries = useCameraProcessingStatuses(
    cameras.map((camera) => camera.id),
  );
  const resolvedAlertIds = useAlertStore((state) => state.resolvedAlertIds);

  const alerts = alertsQuery.data?.map(alertToRecord) ?? [];
  const activeAlerts = alerts.filter(
    (alert) =>
      alert.status === "ACTIVE" && !resolvedAlertIds.includes(alert.id),
  );
  const activeTracks = new Set(
    (summariesQuery.data ?? []).flatMap((summary) =>
      summary.current_detections.map(
        (detection) => `${summary.camera_id}:${detection.track_id}`,
      ),
    ),
  );
  const highRisk = alerts.filter(
    (alert) => alert.risk === "HIGH" || alert.risk === "CRITICAL",
  ).length;
  const activeCameraCount = processingQueries.filter((query) => {
    const runtime = query.data;
    return Boolean(
      runtime &&
        (runtime.status === "PROCESSING" || runtime.status === "ONLINE") &&
        runtime.frames_processed > 0,
    );
  }).length;
  const systemLive = healthQuery.isSuccess && !camerasQuery.isError;

  const metrics = [
    {
      label: "SYSTEM STATUS",
      value: healthQuery.isPending
        ? "CHECKING"
        : systemLive
          ? "ONLINE"
          : "OFFLINE",
      icon: ShieldCheck,
      color: systemLive ? "text-green-300" : "text-orange-300",
    },
    {
      label: "CAMERAS ACTIVE",
      value: cameras.length
        ? `${activeCameraCount} / ${cameras.length} configured`
        : "N/A",
      icon: Camera,
      color: "text-cyan-300",
    },
    {
      label: "ACTIVE ALERTS",
      value: alertsQuery.isLoading
        ? "..."
        : String(activeAlerts.length).padStart(2, "0"),
      icon: AlertTriangle,
      color: "text-orange-300",
    },
    {
      label: "ACTIVE TRACKS",
      value: summariesQuery.isLoading
        ? "..."
        : String(activeTracks.size).padStart(2, "0"),
      icon: Crosshair,
      color: "text-yellow-300",
    },
    {
      label: "HIGH-RISK EVENTS",
      value: alertsQuery.isLoading ? "..." : String(highRisk).padStart(2, "0"),
      icon: Activity,
      color: "text-red-300",
    },
  ];

  return (
    <section className="border border-[#2A3441] bg-[#141A23]">
      <div className="grid grid-cols-2 gap-px bg-[#2A3441] sm:grid-cols-3 xl:grid-cols-5">
        {metrics.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-[#141A23] p-3">
            <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.16em] text-[#8B949E]">
              <Icon size={12} className={color} aria-hidden="true" />
              {label}
            </div>
            <p className="mt-2 text-xl font-semibold text-[#E6EDF3]">{value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default SystemOverview;
