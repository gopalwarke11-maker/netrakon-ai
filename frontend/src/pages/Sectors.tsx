import SectorRiskMap from "../components/map/SectorRiskMap";
import {
  useAlerts,
  useBoundaries,
  useCameras,
  useCameraRuntimeSummaries,
} from "../api/hooks";
import { alertToRecord } from "../api/adapters";
import type { ApiRiskLevel } from "../types/api";

function Sectors() {
  const cameras = useCameras().data ?? [];
  const alerts = useAlerts().data?.map(alertToRecord) ?? [];
  const boundaries = useBoundaries().data ?? [];
  const summaries = useCameraRuntimeSummaries().data ?? [];
  const summaryByCamera = new Map(
    summaries.map((summary) => [summary.camera_id, summary]),
  );
  const sectors = Array.from(
    new Map(
      cameras.map((camera) => {
        const cameraSummary = summaryByCamera.get(camera.id);
        const cameraAlerts = alerts.filter(
          (alert) => alert.cameraId === camera.id && alert.status === "ACTIVE",
        );
        const risk = cameraAlerts.reduce<ApiRiskLevel | "NO DATA">(
          (current, alert) => {
            const order = { "NO DATA": 0, LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 };
            return order[alert.risk] > order[current] ? alert.risk : current;
          },
          "NO DATA",
        );
        return [
          camera.sector.toUpperCase(),
          {
            id: camera.sector.toUpperCase(),
            name: camera.sector,
            cameras: [camera.id],
            risk,
            activeTracks: cameraSummary?.current_detections.length ?? 0,
            confidence: Math.round(
              ((cameraSummary?.average_confidence ?? 0) * 100),
            ),
            boundaries: boundaries
              .filter((boundary) => boundary.camera_id === camera.id && boundary.enabled)
              .map((boundary) => boundary.name),
          },
        ];
      }),
    ).values(),
  );

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 p-4 sm:p-6">
      <header className="border-b border-[#2A3441] pb-4">
        <h1 className="text-lg font-semibold tracking-[0.12em]">SECTORS</h1>
        <p className="mt-1 text-[10px] tracking-wider text-[#8B949E]">
          CONFIGURED ZONES // BACKEND DATA
        </p>
      </header>
      <SectorRiskMap />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {sectors.length === 0 ? (
          <div className="border border-[#2A3441] bg-[#141A23] p-4 text-[10px] text-[#8B949E]">
            NO SECTOR DATA AVAILABLE.
          </div>
        ) : (
          sectors.map((sector) => (
            <div
              key={sector.id}
              className="border border-[#2A3441] bg-[#141A23] p-4"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold">
                  {sector.id} // {sector.name}
                </span>
                <span className="text-[10px] font-bold text-orange-300">
                  {sector.risk}
                </span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3 text-[10px] text-[#8B949E]">
                <span>
                  CAMERAS{" "}
                  <b className="ml-1 text-[#E6EDF3]">
                    {sector.cameras.join(", ")}
                  </b>
                </span>
                <span>
                  STATUS{" "}
                  <b className="ml-1 text-green-300">
                    {sector.activeTracks > 0 ? "ACTIVE" : "STABLE"}
                  </b>
                </span>
                <span>
                  TRACKS{" "}
                  <b className="ml-1 text-[#E6EDF3]">{sector.activeTracks}</b>
                </span>
                <span>
                  CONFIDENCE{" "}
                  <b className="ml-1 text-[#E6EDF3]">{sector.confidence}%</b>
                </span>
                <span className="col-span-2">
                  BOUNDARIES{" "}
                  <b className="ml-1 text-[#E6EDF3]">
                    {sector.boundaries.length
                      ? sector.boundaries.join(", ")
                      : "NO BOUNDARY CONFIGURED"}
                  </b>
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
export default Sectors;
