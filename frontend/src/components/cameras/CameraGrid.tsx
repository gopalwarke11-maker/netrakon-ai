import { useEffect } from "react";
import { Video } from "lucide-react";
import CameraControls from "./CameraControls";
import LiveCamera from "./LiveCamera";
import { useCameraStore } from "../../state/cameraStore";
import { cameraToRecord } from "../../api/adapters";
import { useCameras } from "../../api/hooks";

function CameraGrid() {
  const selectedCamera = useCameraStore((state) => state.selectedCamera);
  const detectionEnabled = useCameraStore((state) => state.detectionEnabled);
  const setSelectedCamera = useCameraStore((state) => state.setSelectedCamera);
  const setViewMode = useCameraStore((state) => state.setViewMode);
  const camerasQuery = useCameras();
  const cameras = camerasQuery.data?.map(cameraToRecord) ?? [];

  useEffect(() => {
    const handleFullscreenChange = () => {
      setViewMode(document.fullscreenElement ? "fullscreen" : "grid");
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, [setViewMode]);

  const handleFullscreen = async () => {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
        return;
      }

      const selectedElement = document.querySelector<HTMLElement>(
        `[data-camera-id="${selectedCamera}"]`,
      );
      if (selectedElement) {
        await selectedElement.requestFullscreen();
      }
    } catch {
      setViewMode("grid");
    }
  };

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Video size={15} className="text-[#3B82F6]" aria-hidden="true" />
          <h2 className="text-xs font-semibold tracking-[0.15em] text-[#E6EDF3]">
            LIVE CAMERA MONITORING
          </h2>
        </div>
        <span className="text-[10px] text-[#8B949E]">
          {camerasQuery.isLoading
            ? "CHECKING FEEDS"
            : `${cameras.length} FEEDS CONNECTED`}
        </span>
      </div>
      {camerasQuery.isError && (
        <div className="mb-3 flex items-center justify-between border border-orange-400/40 bg-orange-400/5 px-3 py-2 text-[10px] text-orange-200">
          <span>BACKEND UNAVAILABLE // NO LIVE CAMERA DATA</span>
          <button
            type="button"
            onClick={() => void camerasQuery.refetch()}
            className="font-bold underline"
          >
            RETRY
          </button>
        </div>
      )}
      {!camerasQuery.isLoading && cameras.length === 0 && (
        <div className="mb-3 border border-[#2A3441] bg-[#0A0E14] px-3 py-2 text-[10px] text-[#8B949E]">
          NO CAMERA CONFIGURATION AVAILABLE FROM BACKEND.
        </div>
      )}
      <CameraControls onFullscreen={() => void handleFullscreen()} />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {cameras.map((camera) => (
          <LiveCamera
            key={camera.cameraId}
            {...camera}
            cameraStatus={camera.status}
            showDetection={detectionEnabled}
            isSelected={camera.cameraId === selectedCamera}
            onSelect={() => setSelectedCamera(camera.cameraId)}
          />
        ))}
      </div>
    </section>
  );
}

export default CameraGrid;
