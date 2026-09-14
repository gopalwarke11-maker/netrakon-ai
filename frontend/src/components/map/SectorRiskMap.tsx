import { useMemo, useState } from "react";
import {
  Camera,
  Map as MapIcon,
  Navigation,
  ShieldAlert,
  Target,
} from "lucide-react";
import {
  useAlerts,
  useBoundaries,
  useCameras,
  useCameraRuntimeSummaries,
} from "../../api/hooks";
import { alertToRecord } from "../../api/adapters";

const riskStyles = {
  LOW: {
    panel: "border-green-500/40 bg-green-500/10 text-green-300",
    marker: "#22c55e",
  },
  MEDIUM: {
    panel: "border-yellow-500/40 bg-yellow-500/10 text-yellow-300",
    marker: "#eab308",
  },
  HIGH: {
    panel: "border-orange-500/40 bg-orange-500/10 text-orange-300",
    marker: "#f97316",
  },
  CRITICAL: {
    panel: "border-red-500/40 bg-red-500/10 text-red-300",
    marker: "#ef4444",
  },
  "NO DATA": {
    panel: "border-[#2A3441] bg-[#0A0E14] text-[#8B949E]",
    marker: "#64748b",
  },
} as const;

type SectorSummary = {
  id: string;
  name: string;
  risk: keyof typeof riskStyles;
  cameras: string[];
  boundaries: string[];
  activeTracks: number;
  latestDetection: string;
  confidence: number;
};

function SectorRiskMap() {
  const camerasQuery = useCameras();
  const boundariesQuery = useBoundaries();
  const summariesQuery = useCameraRuntimeSummaries();
  const alertsQuery = useAlerts();
  const cameraData = useMemo(
    () => camerasQuery.data ?? [],
    [camerasQuery.data],
  );
  const alerts = useMemo(
    () => alertsQuery.data?.map(alertToRecord) ?? [],
    [alertsQuery.data],
  );
  const boundaries = useMemo(
    () => boundariesQuery.data ?? [],
    [boundariesQuery.data],
  );
  const summaries = useMemo(
    () =>
      new Map(
        (summariesQuery.data ?? []).map((summary) => [
          summary.camera_id,
          summary,
        ]),
      ),
    [summariesQuery.data],
  );
  const cameraMarkers = useMemo(() => {
    const columns = Math.max(1, Math.ceil(Math.sqrt(cameraData.length)));
    return cameraData.map((camera, index) => {
      const column = index % columns;
      const row = Math.floor(index / columns);
      const rows = Math.ceil(cameraData.length / columns);
      const runtimeSummary = summaries.get(camera.id);
      const activeAlerts = alerts.filter(
        (alert) => alert.cameraId === camera.id && alert.status === "ACTIVE",
      );
      const risk = activeAlerts.reduce<keyof typeof riskStyles>(
        (current, alert) => {
          const order = {
            "NO DATA": 0,
            LOW: 1,
            MEDIUM: 2,
            HIGH: 3,
            CRITICAL: 4,
          };
          return order[alert.risk] > order[current] ? alert.risk : current;
        },
        "NO DATA",
      );
      const runtimeState = runtimeSummary?.status;
      const state =
        runtimeState === "PROCESSING" || runtimeState === "ONLINE"
          ? "LIVE"
          : runtimeState === "ERROR"
            ? "ERROR"
            : runtimeState === "STOPPED"
              ? "STOPPED"
              : "CONFIGURED";
      return {
        camera,
        state,
        risk,
        tracks: runtimeSummary?.current_detections.length ?? 0,
        left: columns === 1 ? 50 : 10 + (column / (columns - 1)) * 80,
        top: rows === 1 ? 42 : 15 + (row / (rows - 1)) * 68,
      };
    });
  }, [alerts, cameraData, summaries]);
  const sectors = useMemo<SectorSummary[]>(() => {
    const grouped = new Map<string, SectorSummary>();
    for (const camera of cameraData) {
      const sector = camera.sector || "UNASSIGNED";
      const sectorKey = sector.toUpperCase();
      if (!grouped.has(sectorKey)) {
        grouped.set(sectorKey, {
          id: sectorKey,
          name: sector,
          risk: "NO DATA",
          cameras: [],
          boundaries: [],
          activeTracks: 0,
          latestDetection: "NO DATA",
          confidence: 0,
        });
      }
      const entry = grouped.get(sectorKey)!;
      entry.cameras.push(camera.id);
      entry.boundaries.push(
        ...boundaries
          .filter(
            (boundary) => boundary.camera_id === camera.id && boundary.enabled,
          )
          .map((boundary) => boundary.name),
      );
      const runtimeSummary = summaries.get(camera.id);
      entry.activeTracks += runtimeSummary?.current_detections.length ?? 0;
      const currentDetection = runtimeSummary?.current_detections[0];
      if (currentDetection) {
        entry.latestDetection = currentDetection.class_name;
        entry.confidence = Math.max(
          entry.confidence,
          Math.round(currentDetection.confidence * 100),
        );
      }
      const sectorAlerts = alerts.filter(
        (alert) => alert.cameraId === camera.id && alert.status === "ACTIVE",
      );
      if (sectorAlerts.length > 0) {
        entry.latestDetection =
          entry.latestDetection === "NO DATA"
            ? sectorAlerts[0].objectType
            : entry.latestDetection;
        entry.confidence = Math.max(
          entry.confidence,
          Math.round(sectorAlerts[0].confidence ?? 0),
        );
        const highestRisk = sectorAlerts.reduce(
          (current, alert) => {
            const order = {
              "NO DATA": 0,
              LOW: 1,
              MEDIUM: 2,
              HIGH: 3,
              CRITICAL: 4,
            };
            return order[alert.risk] > order[current] ? alert.risk : current;
          },
          "NO DATA" as keyof typeof riskStyles,
        );
        entry.risk = highestRisk;
      }
    }
    return [...grouped.values()];
  }, [alerts, boundaries, cameraData, summaries]);

  const [selectedSector, setSelectedSector] = useState<SectorSummary | null>(
    null,
  );
  const selected = selectedSector ?? sectors[0] ?? null;

  return (
    <section className="mt-4 overflow-hidden border border-[#2A3441] bg-[#141A23]">
      <div className="flex items-center justify-between border-b border-[#2A3441] px-4 py-3">
        <div className="flex items-center gap-2">
          <MapIcon size={15} className="text-[#3B82F6]" aria-hidden="true" />
          <h2 className="text-xs font-semibold tracking-[0.15em]">
            SECTOR RISK MAP
          </h2>
        </div>
        <span className="text-[10px] text-[#8B949E]">
          {sectors.length ? "CONCEPTUAL MAP" : "NO DATA"}
        </span>
      </div>
      {sectors.length === 0 ? (
        <div className="p-4 text-[10px] text-[#8B949E]">
          NO CONFIGURED SECTORS OR ALERT DATA.
        </div>
      ) : (
        <div className="grid gap-4 p-4 lg:grid-cols-[1.6fr_1fr]">
          <div className="relative aspect-[16/9] min-h-60 overflow-hidden border border-[#2A3441] bg-[#080B10]">
            <div
              className="absolute inset-0 opacity-25"
              style={{
                backgroundImage:
                  "linear-gradient(#2A3441 1px, transparent 1px), linear-gradient(90deg, #2A3441 1px, transparent 1px)",
                backgroundSize: "28px 28px",
              }}
            />
            <svg
              className="absolute inset-0 h-full w-full p-3"
              viewBox="0 0 100 100"
              role="img"
              aria-label="Conceptual sector risk map"
            >
              <path
                d="M3 88 C22 73 26 88 43 73 S74 80 97 63"
                fill="none"
                stroke="#3B82F6"
                strokeDasharray="3 2"
                strokeWidth="1.1"
              />
              <path
                d="M4 90 L96 65"
                fill="none"
                stroke="#ef4444"
                strokeDasharray="1.5 2"
                strokeWidth="1.2"
              />
              <text
                x="68"
                y="64"
                fill="#f87171"
                fontSize="3.2"
                letterSpacing=".5"
              >
                RESTRICTED AREA
              </text>
            </svg>
            {cameraMarkers.map((marker) => (
              <button
                key={marker.camera.id}
                type="button"
                onClick={() => {
                  const sector = sectors.find(
                    (item) => item.name === marker.camera.sector,
                  );
                  if (sector) setSelectedSector(sector);
                }}
                className="absolute -translate-x-1/2 -translate-y-1/2 border border-[#2A3441] bg-[#0A0E14]/95 px-1.5 py-1 text-left shadow-lg"
                style={{ left: `${marker.left}%`, top: `${marker.top}%` }}
                title={`${marker.camera.id} // ${marker.camera.sector}`}
              >
                <span className="flex items-center gap-1 text-[8px] font-bold text-[#E6EDF3]">
                  <Camera
                    size={10}
                    color={riskStyles[marker.risk].marker}
                    aria-hidden="true"
                  />
                  {marker.camera.id}
                </span>
                <span className="block text-[7px] text-[#8B949E]">
                  {marker.state} // TRACKS {marker.tracks}
                </span>
                <span
                  className="block text-[7px]"
                  style={{ color: riskStyles[marker.risk].marker }}
                >
                  RISK {marker.risk}
                </span>
              </button>
            ))}
            <div className="absolute inset-x-3 bottom-8 grid max-h-24 grid-cols-2 gap-1 overflow-auto sm:grid-cols-3">
              {sectors.flatMap((sector) =>
                sector.cameras.map((cameraId) => (
                  <button
                    key={cameraId}
                    type="button"
                    onClick={() => setSelectedSector(sector)}
                    className="border border-[#2A3441] bg-[#0A0E14]/90 p-1.5 text-left text-[8px] text-cyan-200"
                  >
                    {cameraId} // {sector.name}
                  </button>
                )),
              )}
            </div>
            <div className="absolute bottom-2 left-3 flex items-center gap-2 text-[8px] tracking-[0.2em] text-red-400">
              <span className="h-px w-5 bg-red-400" /> BORDER LINE
            </div>
            <div className="absolute right-3 top-3 flex items-center gap-1 text-[8px] text-blue-300">
              <Navigation size={10} aria-hidden="true" /> PATROL ROUTE
            </div>
          </div>
          {selected && (
            <div className={`border p-4 ${riskStyles[selected.risk].panel}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={15} aria-hidden="true" />
                  <span className="text-xs font-bold tracking-wider">
                    {selected.name}
                  </span>
                </div>
                <span className="text-[10px] font-bold">{selected.risk}</span>
              </div>
              <dl className="mt-5 grid grid-cols-2 gap-4 text-[10px]">
                <div>
                  <dt className="opacity-60">CAMERAS</dt>
                  <dd className="mt-1 text-[#E6EDF3]">
                    {selected.cameras.join(", ") || "NONE"}
                  </dd>
                </div>
                <div>
                  <dt className="opacity-60">ACTIVE TRACKS</dt>
                  <dd className="mt-1 text-[#E6EDF3]">
                    {selected.activeTracks}
                  </dd>
                </div>
                <div className="col-span-2">
                  <dt className="opacity-60">BOUNDARIES</dt>
                  <dd className="mt-1 text-[#E6EDF3]">
                    {selected.boundaries.length
                      ? selected.boundaries.join(", ")
                      : "NO BOUNDARY CONFIGURED"}
                  </dd>
                </div>
                <div>
                  <dt className="opacity-60">LATEST DETECTION</dt>
                  <dd className="mt-1 text-[#E6EDF3]">
                    {selected.latestDetection}
                  </dd>
                </div>
                <div>
                  <dt className="opacity-60">CONFIDENCE</dt>
                  <dd className="mt-1 text-[#E6EDF3]">
                    {selected.confidence}%
                  </dd>
                </div>
              </dl>
              <div className="mt-6 space-y-3 border-t border-current/20 pt-4 text-[10px] opacity-80">
                <p className="flex items-center gap-2">
                  <Camera size={12} aria-hidden="true" /> Camera locations
                </p>
                <p className="flex items-center gap-2">
                  <Target size={12} aria-hidden="true" /> Detection markers
                </p>
                <p className="flex items-center gap-2">
                  <Navigation size={12} aria-hidden="true" /> Patrol route
                  active
                </p>
              </div>
            </div>
          )}
        </div>
      )}
      <div className="flex flex-wrap gap-4 border-t border-[#2A3441] px-4 py-3 text-[9px] text-[#8B949E]">
        <span>
          <i className="mr-1.5 inline-block size-2 rounded-full bg-green-400" />
          LOW
        </span>
        <span>
          <i className="mr-1.5 inline-block size-2 rounded-full bg-yellow-400" />
          MEDIUM
        </span>
        <span>
          <i className="mr-1.5 inline-block size-2 rounded-full bg-orange-400" />
          HIGH
        </span>
        <span>
          <i className="mr-1.5 inline-block size-2 rounded-full bg-red-500" />
          CRITICAL
        </span>
      </div>
    </section>
  );
}

export default SectorRiskMap;
