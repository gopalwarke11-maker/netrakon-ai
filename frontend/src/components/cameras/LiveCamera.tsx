import { Camera, Minimize2, Radio } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import DetectionOverlay from "./DetectionOverlay";
import {
  useCameraBehaviors,
  useCameraProcessingStatus,
  useCameraRuntimeSummary,
} from "../../api/hooks";
import {
  getCameraStreamUrl,
  getProcessedCameraStreamUrl,
  startCamera,
} from "../../api/cameras";
import { ApiError } from "../../api/client";

interface LiveCameraProps {
  cameraId: string;
  name?: string;
  sourceType?: string;
  cameraStatus?: string;
  sector: string;
  streamUrl?: string | null;
  showDetection?: boolean;
  isSelected?: boolean;
  onSelect?: () => void;
}

type CameraStatus = "requesting" | "ready" | "offline" | "error";

function LiveCamera({
  cameraId,
  name,
  sourceType,
  sector,
  streamUrl,
  showDetection = false,
  isSelected = false,
  onSelect,
}: LiveCameraProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState<CameraStatus>("requesting");
  const [errorMessage, setErrorMessage] = useState("CONNECTING...");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const processingQuery = useCameraProcessingStatus(cameraId);
  const summaryQuery = useCameraRuntimeSummary(cameraId);
  const behaviorQuery = useCameraBehaviors(cameraId);
  const processingStatus = processingQuery.data?.status;
  const latestBehavior = behaviorQuery.data?.[0];
  const currentDetections = summaryQuery.data?.current_detections ?? [];
  const summaryProcessorActive =
    summaryQuery.data?.status === "ONLINE" ||
    summaryQuery.data?.status === "PROCESSING";
  const visibleDetections = summaryProcessorActive ? currentDetections : [];
  const classCounts = summaryQuery.data?.detection_class_counts ?? {};
  const averageConfidence = summaryQuery.data?.average_confidence;
  const sessionDetections = summaryQuery.data?.total_detections;
  const historicalTracks = summaryQuery.data?.historical_tracks.length;

  useEffect(() => {
    let isMounted = true;
    const videoElement = videoRef.current;

    const initializeCamera = async () => {
      if (!streamUrl || !["FILE", "MJPEG", "RTSP"].includes(sourceType ?? "")) {
        if (isMounted) {
          setStatus("offline");
          setErrorMessage(
            !streamUrl
              ? "NO CONFIGURED SOURCE // PROCESSOR STATUS ONLY"
              : "NO BROWSER STREAM // PROCESSOR STATUS ONLY",
          );
        }
        return;
      }

      try {
        await startCamera(cameraId, sourceType === "FILE");
      } catch (error) {
        // A management view may have started this processor already.
        if (!(error instanceof ApiError && error.status === 409)) {
          if (isMounted) {
            setStatus("error");
            setErrorMessage("BACKEND PROCESSOR START FAILED");
          }
          return;
        }
      }

      if (videoElement && sourceType === "FILE") {
        videoElement.src = getCameraStreamUrl(cameraId);
      }
    };

    void initializeCamera();

    return () => {
      isMounted = false;
      if (videoElement) {
        videoElement.srcObject = null;
        videoElement.removeAttribute("src");
      }
    };
  }, [cameraId, sourceType, streamUrl]);

  const framesProcessed = processingQuery.data?.frames_processed ?? 0;
  const hasSource = Boolean(streamUrl);
  const processorLive =
    (processingStatus === "ONLINE" || processingStatus === "PROCESSING") &&
    framesProcessed > 0;
  const isLive = processorLive && status === "ready";
  const videoVisible = status === "ready";
  const displayStatus = !hasSource
    ? "CONFIGURED"
    : processingQuery.data?.error || processingStatus === "ERROR"
      ? "ERROR"
      : processorLive
        ? "LIVE"
        : processingStatus === "ONLINE" || processingStatus === "PROCESSING"
          ? "STARTING"
          : processingStatus === "STOPPED" && framesProcessed > 0
            ? sourceType === "FILE" && !processingQuery.data?.loop_enabled
              ? "VIDEO ENDED"
              : "STOPPED"
            : processingStatus === "OFFLINE" && sourceType !== "FILE"
              ? "OFFLINE"
              : "STOPPED";
  const statusTone =
    displayStatus === "LIVE" ? "text-green-400" : "text-yellow-300";
  const backendDetectionState = processorLive
    ? "ON"
    : processingStatus === "STOPPED" && framesProcessed > 0
      ? "STOPPED"
      : "UNKNOWN";

  const handleVideoLoaded = () => {
    setStatus("ready");
    setErrorMessage("");
  };

  const handleVideoError = () => {
    setStatus("error");
    setErrorMessage("BROWSER FILE STREAM UNAVAILABLE");
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(
        document.fullscreenElement?.getAttribute("data-camera-id") === cameraId,
      );
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, [cameraId]);

  return (
    <article
      className={`overflow-hidden rounded-lg border bg-[#141A23] ${isSelected ? "border-[#3B82F6]" : "border-[#2A3441]"}`}
      data-camera-id={cameraId}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") onSelect?.();
      }}
      tabIndex={onSelect ? 0 : undefined}
    >
      <div className="flex h-10 items-center justify-between border-b border-[#2A3441] px-3">
        <div className="flex items-center gap-2">
          <Camera size={14} className="text-[#3B82F6]" aria-hidden="true" />
          <span className="min-w-0 text-xs font-semibold text-[#E6EDF3]">
            {name ?? cameraId}{" "}
            <span className="font-normal text-[#8B949E]">// {sector}</span>
          </span>
        </div>
        <div
          className={`flex items-center gap-1.5 text-[9px] font-bold tracking-wider ${statusTone}`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${displayStatus === "LIVE" ? "bg-green-400" : "bg-yellow-300"}`}
          />
          {displayStatus}
        </div>
      </div>

      <div className="relative aspect-video overflow-hidden bg-[#080B10]">
        {sourceType === "FILE" ? <video
          ref={videoRef}
          className={`h-full w-full object-cover ${videoVisible ? "block" : "hidden"}`}
          autoPlay
          playsInline
          muted
          controls
          loop={processingQuery.data?.loop_enabled ?? false}
          onLoadedData={handleVideoLoaded}
          onError={handleVideoError}
          aria-label={`${cameraId} live camera feed`}
        /> : <img
          className={`h-full w-full object-contain ${videoVisible ? "block" : "hidden"}`}
          src={processorLive ? getProcessedCameraStreamUrl(cameraId) : undefined}
          onLoad={handleVideoLoaded}
          onError={handleVideoError}
          alt={`${cameraId} processed live camera feed`}
        />}
        {!videoVisible && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-4 text-center text-[#8B949E]">
            <Camera size={28} strokeWidth={1.25} aria-hidden="true" />
            <span className="text-[10px] tracking-[0.15em]">
              {processingQuery.data?.error ?? errorMessage}
            </span>
          </div>
        )}
        {videoVisible && (
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 bg-black/75 px-2 py-1 text-[8px] font-bold tracking-[0.14em] text-[#8B949E]">
            {!showDetection
              ? "DETECTION DISPLAY OFF"
              : visibleDetections.length
                ? `DETECTION ${backendDetectionState}`
                : "NO CURRENT DETECTIONS"}
          </div>
        )}
        <DetectionOverlay
          visible={isLive && showDetection}
          detections={visibleDetections}
        />
        <div className="absolute bottom-2 left-2 bg-black/70 px-2 py-1 font-mono text-[10px] text-[#E6EDF3]">
          {cameraId}
        </div>
        <div className="absolute right-2 top-2 flex items-center gap-1 rounded bg-black/70 px-2 py-1 text-[9px] font-semibold text-cyan-300">
          <Radio size={11} aria-hidden="true" />
          AI MONITORING
        </div>
        {isFullscreen && (
          <>
            <button
              type="button"
              onClick={() => void document.exitFullscreen()}
              className="absolute left-2 top-2 flex items-center gap-1 border border-[#2A3441] bg-black/80 px-2 py-1 text-[9px] font-bold text-[#E6EDF3]"
            >
              <Minimize2 size={11} aria-hidden="true" />
              CLOSE VIEW
            </button>
            <div className="absolute bottom-2 right-2 bg-black/75 px-2 py-1 font-mono text-[9px] text-[#8B949E]">
              DETECTION {showDetection ? "ON" : "OFF"} // TRACKING UI // REC
              READY
            </div>
          </>
        )}
      </div>
      <div className="grid grid-cols-3 gap-y-1 border-t border-[#2A3441] bg-[#141A23] px-3 py-2 text-[9px] text-[#8B949E] sm:grid-cols-6">
        <span>SRC {sourceType ?? "N/A"}</span>
        <span>
          FPS {processingQuery.data?.processing_fps.toFixed(1) ?? "--"}
        </span>
        <span>RES {processingQuery.data?.resolution ?? "--"}</span>
        <span>ACTIVE TRACKS {processingQuery.data?.active_tracks ?? "--"}</span>
        <span>CURRENT DET {currentDetections.length}</span>
        <span>SESSION DET {sessionDetections ?? "--"}</span>
        <span>HISTORICAL TRACKS {historicalTracks ?? "--"}</span>
        <span
          title={Object.entries(classCounts)
            .map(([label, count]) => `${label}: ${count}`)
            .join(", ")}
        >
          CLASSES{" "}
          {Object.entries(classCounts).length
            ? Object.entries(classCounts)
                .map(([label, count]) => `${label} ${count}`)
                .join(" // ")
            : "--"}
        </span>
        <span>
          CONF{" "}
          {averageConfidence == null
            ? "--"
            : `${Math.round(averageConfidence * 100)}%`}
        </span>
        <span
          title={
            latestBehavior ? `Track ${latestBehavior.track_id}` : undefined
          }
        >
          BEHAVIOR {latestBehavior?.primary_behavior ?? "--"}{" "}
          {latestBehavior ? latestBehavior.behavior_score : ""}
        </span>
      </div>
    </article>
  );
}

export default LiveCamera;
