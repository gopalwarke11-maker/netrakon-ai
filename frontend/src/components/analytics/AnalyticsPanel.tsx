import { BarChart3, TrendingUp } from "lucide-react";
import {
  useAlerts,
  useBackendHealth,
  useCameras,
  useCameraProcessingStatuses,
  useCameraRuntimeSummaries,
} from "../../api/hooks";
import { alertToRecord } from "../../api/adapters";

function AnalyticsPanel() {
  const healthQuery = useBackendHealth();
  const camerasQuery = useCameras();
  const alertsQuery = useAlerts();
  const summariesQuery = useCameraRuntimeSummaries();

  const cameraCount = camerasQuery.data?.length ?? 0;
  const processingQueries = useCameraProcessingStatuses(
    (camerasQuery.data ?? []).map((camera) => camera.id),
  );
  const activeCameraCount = processingQueries.filter((query) => {
    const runtime = query.data;
    return Boolean(
      runtime &&
        (runtime.status === "PROCESSING" || runtime.status === "ONLINE") &&
        runtime.frames_processed > 0,
    );
  }).length;
  const alerts = alertsQuery.data?.map(alertToRecord) ?? [];
  const summaries = summariesQuery.data ?? [];
  const totalDetections = summaries.reduce(
    (sum, summary) => sum + summary.total_detections,
    0,
  );
  const totalTracks = summaries.reduce(
    (sum, summary) => sum + summary.historical_tracks.length,
    0,
  );
  const totalIntrusions =
    summaries.reduce((sum, summary) => sum + summary.intrusions.length, 0) ||
    new Set(
      alerts.filter((alert) => alert.eventId).map((alert) => alert.eventId),
    ).size;
  const classCounts = summaries.reduce<Record<string, number>>(
    (counts, summary) => {
      for (const [label, count] of Object.entries(
        summary.detection_class_counts,
      )) {
        counts[label] = (counts[label] ?? 0) + count;
      }
      return counts;
    },
    {},
  );
  const riskCounts = {
    LOW: alerts.filter((alert) => alert.risk === "LOW").length,
    MEDIUM: alerts.filter((alert) => alert.risk === "MEDIUM").length,
    HIGH: alerts.filter((alert) => alert.risk === "HIGH").length,
    CRITICAL: alerts.filter((alert) => alert.risk === "CRITICAL").length,
  };
  const weightedConfidence = summaries.reduce(
    (sum, summary) =>
      sum + (summary.average_confidence ?? 0) * summary.total_detections,
    0,
  );
  const avgConfidence = totalDetections
    ? Math.round((weightedConfidence / totalDetections) * 100)
    : 0;
  const chartData = summaries.map((summary) => summary.total_detections);
  const maxTrend = Math.max(...chartData, 1);
  const riskSummary = Object.entries(riskCounts).map(([label, value]) => ({
    label,
    value,
    percent: alerts.length ? Math.round((value / alerts.length) * 100) : 0,
  }));

  const hasData =
    healthQuery.isSuccess &&
    (cameraCount > 0 || alerts.length > 0 || totalDetections > 0);

  return (
    <section className="mt-4 border border-[#2A3441] bg-[#141A23]">
      <div className="flex items-center justify-between border-b border-[#2A3441] px-4 py-3">
        <div className="flex items-center gap-2">
          <BarChart3 size={15} className="text-[#3B82F6]" aria-hidden="true" />
          <h2 className="text-xs font-semibold tracking-[0.15em]">ANALYTICS</h2>
        </div>
        <span className="text-[10px] text-cyan-300">
          {totalDetections > 0
            ? "SESSION + LIVE DATA"
            : hasData
              ? "LIVE DATA"
              : "NO DATA"}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-px bg-[#2A3441] sm:grid-cols-3 lg:grid-cols-6">
        {[
          ["SESSION DETECTIONS", String(totalDetections)],
          ["HISTORICAL TRACKS", String(totalTracks)],
          ["INTRUSION EVENTS", String(totalIntrusions)],
          [
            "ACTIVE ALERTS",
            String(alerts.filter((alert) => alert.status === "ACTIVE").length),
          ],
          [
            "HIGH-RISK EVENTS",
            String(
              alerts.filter(
                (alert) => alert.risk === "HIGH" || alert.risk === "CRITICAL",
              ).length,
            ),
          ],
          ["TRACKED PERSONS", String(classCounts.person ?? 0)],
          [
            "CAMERAS ACTIVE",
            `${activeCameraCount}/${cameraCount || 0} configured`,
          ],
          ["AVG CONFIDENCE", `${avgConfidence}%`],
        ].map(([label, value]) => (
          <div key={label} className="bg-[#141A23] p-3">
            <p className="text-[9px] leading-tight text-[#8B949E]">{label}</p>
            <p className="mt-1 text-lg font-semibold">{value}</p>
          </div>
        ))}
      </div>
      {!hasData ? (
        <div className="p-4 text-[10px] text-[#8B949E]">
          INSUFFICIENT DATA FOR ANALYTICS.
        </div>
      ) : (
        <>
          <div className="grid gap-4 p-4 lg:grid-cols-[1.4fr_1fr]">
            <div>
              <div className="mb-3 flex items-center gap-2 text-[10px] font-semibold tracking-wider text-[#8B949E]">
                <TrendingUp size={13} aria-hidden="true" /> SESSION DETECTIONS
                // BY CAMERA
              </div>
              <div className="flex h-28 items-end gap-1 border-b border-l border-[#2A3441] px-2">
                {chartData.map((value, index) => (
                  <div
                    key={`${value}-${index}`}
                    className="flex-1 bg-[#3B82F6]/60 transition hover:bg-[#3B82F6]"
                    style={{ height: `${(value / maxTrend) * 100}%` }}
                    title={`${value} detections`}
                  />
                ))}
              </div>
            </div>
            <div>
              <p className="mb-3 text-[10px] font-semibold tracking-wider text-[#8B949E]">
                ALERT RISK BREAKDOWN
              </p>
              <div className="space-y-3">
                {riskSummary.map(({ label, value, percent }) => (
                  <div
                    key={label}
                    className="flex items-center gap-3 text-[10px]"
                  >
                    <span className="w-14 text-[#8B949E]">{label}</span>
                    <div className="h-2 flex-1 bg-[#0A0E14]">
                      <div
                        className="h-full bg-orange-400/80"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                    <span className="w-5 text-right text-[#E6EDF3]">
                      {value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

export default AnalyticsPanel;
