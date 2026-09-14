import type { ApiTrackedObject } from "../../types/api";

interface DetectionOverlayProps {
  visible?: boolean;
  detections: ApiTrackedObject[];
}

function DetectionOverlay({
  visible = true,
  detections,
}: DetectionOverlayProps) {
  if (!visible || detections.length === 0) return null;

  return (
    <div
      className="pointer-events-none absolute inset-0"
      aria-label="AI detection overlay"
    >
      {detections.map((detection) => {
        const box = detection.bounding_box;
        const imageWidth = detection.image_width ?? 1280;
        const imageHeight = detection.image_height ?? 720;
        return (
          <div
            key={`${detection.track_id}-${box.x1}-${box.y1}`}
            className="absolute border border-orange-400/90"
            style={{
              left: `${(box.x1 / imageWidth) * 100}%`,
              top: `${(box.y1 / imageHeight) * 100}%`,
              width: `${(box.width / imageWidth) * 100}%`,
              height: `${(box.height / imageHeight) * 100}%`,
            }}
          >
            <div className="absolute -left-px -top-5 whitespace-nowrap bg-orange-400 px-1.5 py-0.5 text-[8px] font-bold text-[#0A0E14]">
              {detection.class_name.toUpperCase()}{" "}
              {Math.round(detection.confidence * 100)}%
            </div>
            <div className="absolute -bottom-5 left-0 whitespace-nowrap bg-[#0A0E14]/90 px-1.5 py-0.5 font-mono text-[8px] text-[#E6EDF3]">
              TRACK {detection.track_id}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default DetectionOverlay;
