import { Circle, Grid2X2, Maximize2, ScanFace, Route } from "lucide-react";
import { useCameraStore } from "../../state/cameraStore";

interface CameraControlsProps {
  onFullscreen: () => void;
}

function CameraControls({ onFullscreen }: CameraControlsProps) {
  const detectionEnabled = useCameraStore((state) => state.detectionEnabled);
  const trackingEnabled = useCameraStore((state) => state.trackingEnabled);
  const recording = useCameraStore((state) => state.recording);
  const viewMode = useCameraStore((state) => state.viewMode);
  const toggleDetection = useCameraStore((state) => state.toggleDetection);
  const toggleTracking = useCameraStore((state) => state.toggleTracking);
  const toggleRecording = useCameraStore((state) => state.toggleRecording);
  const setViewMode = useCameraStore((state) => state.setViewMode);

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 border border-[#2A3441] bg-[#141A23] p-3">
      <span className="mr-2 w-full text-[10px] font-semibold tracking-[0.16em] text-[#8B949E] sm:w-auto">
        CAMERA CONTROLS
      </span>
      <button
        type="button"
        onClick={toggleDetection}
        className={`flex items-center gap-2 border px-3 py-2 text-[10px] font-bold tracking-wider transition ${detectionEnabled ? "border-green-500/50 text-green-300" : "border-[#2A3441] text-[#8B949E]"}`}
        aria-pressed={detectionEnabled}
      >
        <ScanFace size={13} aria-hidden="true" />
        DETECTION DISPLAY {detectionEnabled ? "ON" : "OFF"}
      </button>
      <button
        type="button"
        onClick={toggleTracking}
        className={`flex items-center gap-2 border px-3 py-2 text-[10px] font-bold tracking-wider transition ${trackingEnabled ? "border-cyan-400/50 text-cyan-300" : "border-[#2A3441] text-[#8B949E]"}`}
        aria-pressed={trackingEnabled}
      >
        <Route size={13} aria-hidden="true" />
        {trackingEnabled ? "TRACKING ACTIVE" : "TRACKING OFF"}
      </button>
      <button
        type="button"
        onClick={toggleRecording}
        className={`flex items-center gap-2 border px-3 py-2 text-[10px] font-bold tracking-wider transition ${recording ? "border-red-500/50 text-red-300" : "border-[#2A3441] text-[#8B949E]"}`}
        aria-pressed={recording}
      >
        <Circle
          size={11}
          fill={recording ? "currentColor" : "none"}
          aria-hidden="true"
        />
        {recording ? "REC" : "RECORDING OFF"}
      </button>
      <div className="ml-auto flex gap-2">
        <button
          type="button"
          onClick={() => setViewMode("grid")}
          className={`grid size-8 place-items-center border transition ${viewMode === "grid" ? "border-[#3B82F6] text-[#3B82F6]" : "border-[#2A3441] text-[#8B949E] hover:text-[#E6EDF3]"}`}
          aria-label="Grid view"
          aria-pressed={viewMode === "grid"}
          title="Grid view"
        >
          <Grid2X2 size={15} aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={onFullscreen}
          className={`grid size-8 place-items-center border transition ${viewMode === "fullscreen" ? "border-[#3B82F6] text-[#3B82F6]" : "border-[#2A3441] text-[#8B949E] hover:text-[#E6EDF3]"}`}
          aria-label="Fullscreen selected camera"
          aria-pressed={viewMode === "fullscreen"}
          title="Fullscreen selected camera"
        >
          <Maximize2 size={15} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

export default CameraControls;
