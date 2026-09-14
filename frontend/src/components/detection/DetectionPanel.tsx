import { useMemo } from "react";
import { Activity, Crosshair, ScanFace } from "lucide-react";
import { useDetectionStore } from "../../state/detectionStore";
import { useCameraRuntimeSummaries } from "../../api/hooks";
import type { RiskLevel } from "../../data/mockData";

const riskColors: Record<RiskLevel, string> = {
  LOW: "text-green-300",
  MEDIUM: "text-yellow-300",
  HIGH: "text-orange-300",
  CRITICAL: "text-red-300",
};

function DetectionPanel() {
  const selectedTrackId = useDetectionStore((state) => state.selectedTrackId);
  const setSelectedTrack = useDetectionStore((state) => state.setSelectedTrack);
  const summariesQuery = useCameraRuntimeSummaries();
  const summaries = useMemo(
    () => summariesQuery.data ?? [],
    [summariesQuery.data],
  );
  const tracks = useMemo(
    () =>
      summaries.flatMap((summary) => {
        const activeIds = new Set(
          summary.current_detections.map((detection) => detection.track_id),
        );
        return summary.historical_tracks.map((track) => ({
          trackId: `${summary.camera_id}:${track.track_id}`,
          rawTrackId: track.track_id,
          objectType: track.class_name,
          confidence: Math.round((summary.average_confidence ?? 0) * 100),
          cameraId: summary.camera_id,
          sector: "BACKEND SESSION",
          risk: "LOW" as RiskLevel,
          firstDetected: `FRAME ${track.first_seen_frame}`,
          lastSeen: `FRAME ${track.last_seen_frame}`,
          direction: "NOT AVAILABLE",
          speed: "NOT AVAILABLE",
          status: activeIds.has(track.track_id)
            ? ("ACTIVE" as const)
            : ("LOST" as const),
          framesSeen: track.frames_seen,
        }));
      }),
    [summaries],
  );
  const selectedTrack = useMemo(
    () =>
      tracks.find((track) => track.trackId === selectedTrackId) ?? tracks[0],
    [selectedTrackId, tracks],
  );
  const totalDetections = summaries.reduce(
    (sum, summary) => sum + summary.total_detections,
    0,
  );
  const persons = summaries.reduce(
    (sum, summary) => sum + (summary.detection_class_counts.person ?? 0),
    0,
  );
  const vehicles = summaries.reduce(
    (sum, summary) =>
      sum +
      Object.entries(summary.detection_class_counts)
        .filter(([label]) =>
          ["car", "truck", "bus", "motorcycle", "bicycle"].includes(
            label.toLowerCase(),
          ),
        )
        .reduce((count, [, value]) => count + value, 0),
    0,
  );
  const activeTracks = summaries.reduce(
    (sum, summary) =>
      sum +
      new Set(summary.current_detections.map((detection) => detection.track_id))
        .size,
    0,
  );
  const metrics = [
    [
      "TOTAL DETECTIONS",
      summariesQuery.isLoading ? "..." : String(totalDetections),
    ],
    ["ACTIVE TRACKS", summariesQuery.isLoading ? "..." : String(activeTracks)],
    ["PERSONS", String(persons)],
    ["VEHICLES", String(vehicles)],
    [
      "UNKNOWN OBJECTS",
      String(Math.max(0, totalDetections - persons - vehicles)),
    ],
  ];

  return (
    <section className="border border-[#2A3441] bg-[#141A23]">
      <div className="flex items-center justify-between border-b border-[#2A3441] px-4 py-3">
        <div className="flex items-center gap-2">
          <ScanFace size={15} className="text-cyan-300" aria-hidden="true" />
          <h2 className="text-xs font-semibold tracking-[0.15em]">
            DETECTION &amp; TRACKING
          </h2>
        </div>
        <span className="text-[10px] text-cyan-300">
          {summariesQuery.isError
            ? "BACKEND UNAVAILABLE"
            : summariesQuery.isLoading
              ? "LOADING"
              : "LIVE BACKEND"}
        </span>
      </div>
      {summariesQuery.isLoading && (
        <p className="border-b border-[#2A3441] px-4 py-2 text-[10px] text-[#8B949E]">
          LOADING DETECTIONS...
        </p>
      )}
      {summariesQuery.isError && (
        <div className="flex items-center justify-between border-b border-orange-400/40 bg-orange-400/5 px-4 py-2 text-[10px] text-orange-200">
          <span>BACKEND UNAVAILABLE // NO DETECTION DATA</span>
          <button
            type="button"
            onClick={() => void summariesQuery.refetch()}
            className="font-bold underline"
          >
            RETRY
          </button>
        </div>
      )}
      <div className="grid grid-cols-2 gap-px border-b border-[#2A3441] bg-[#2A3441] sm:grid-cols-3">
        {metrics.map(([label, value]) => (
          <div key={label} className="bg-[#141A23] p-3">
            <p className="text-[9px] leading-tight text-[#8B949E]">{label}</p>
            <p className="mt-1 text-lg font-semibold text-[#E6EDF3]">{value}</p>
          </div>
        ))}
      </div>
      <div className="divide-y divide-[#2A3441]">
        {!summariesQuery.isLoading && tracks.length === 0 && (
          <p className="p-5 text-xs text-[#8B949E]">
            NO ACTIVE TRACKS // NO DETECTION DATA
          </p>
        )}
        {tracks.map((track) => (
          <button
            key={track.trackId}
            type="button"
            onClick={() => setSelectedTrack(track.trackId)}
            className={`flex w-full items-center justify-between p-3 text-left hover:bg-[#0A0E14] ${selectedTrack.trackId === track.trackId ? "bg-[#0A0E14]" : ""}`}
          >
            <div className="flex items-center gap-3">
              <span className="grid size-7 place-items-center border border-cyan-400/40 text-cyan-300">
                <Crosshair size={13} aria-hidden="true" />
              </span>
              <div>
                <p className="text-xs font-bold">
                  {track.rawTrackId}{" "}
                  <span className="ml-1 font-normal text-[#8B949E]">
                    {track.objectType}
                  </span>
                </p>
                <p className="mt-1 text-[10px] text-[#8B949E]">
                  {track.cameraId} // {track.sector}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className={`text-xs font-bold ${riskColors[track.risk]}`}>
                {track.confidence}%
              </p>
              <p className="mt-1 text-[9px] text-[#8B949E]">{track.risk}</p>
            </div>
          </button>
        ))}
      </div>
      {selectedTrack && (
        <div className="border-t border-[#2A3441] p-4">
          <div className="flex items-center justify-between">
            <span className="text-[10px] tracking-[0.15em] text-[#8B949E]">
              SELECTED TRACK
            </span>
            <span className="flex items-center gap-1 text-[9px] text-green-300">
              <Activity size={11} aria-hidden="true" />
              {selectedTrack.status}
            </span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 text-[10px]">
            {[
              ["TRACK ID", selectedTrack.rawTrackId],
              ["OBJECT", selectedTrack.objectType],
              ["CONFIDENCE", `${selectedTrack.confidence}%`],
              ["CAMERA", selectedTrack.cameraId],
              ["SECTOR", selectedTrack.sector],
              ["RISK", selectedTrack.risk],
              ["FIRST DETECTED", selectedTrack.firstDetected],
              ["LAST SEEN", selectedTrack.lastSeen],
              ["DIRECTION", selectedTrack.direction],
              ["SPEED", selectedTrack.speed],
              ["OBSERVATIONS", selectedTrack.framesSeen],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-[#8B949E]">{label}</dt>
                <dd
                  className={`mt-0.5 ${label === "RISK" ? riskColors[selectedTrack.risk] : "text-[#E6EDF3]"}`}
                >
                  {value}
                </dd>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

export default DetectionPanel;
