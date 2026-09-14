import type { ApiAlert, ApiCamera, ApiDetection } from "../types/api";
import type { AlertRecord, CameraRecord, TrackRecord } from "../data/mockData";

const toPercent = (value: number | null) => Math.round((value ?? 0) * 100);

export function cameraToRecord(camera: ApiCamera): CameraRecord {
  return {
    cameraId: camera.id,
    name: camera.name,
    sector: camera.sector,
    location: camera.location,
    status: camera.status,
    sourceType: camera.source_type ?? (camera.stream_url?.startsWith("rtsp")
      ? "RTSP"
      : camera.stream_url?.startsWith("http")
        ? "MJPEG"
        : camera.stream_url
          ? "FILE"
          : "NOT CONFIGURED"),
    streamUrl: camera.stream_url,
    showDetection: false,
  };
}

export function alertToRecord(alert: ApiAlert): AlertRecord {
  return {
    id: alert.id,
    timestamp: new Date(alert.timestamp).toLocaleTimeString([], {
      hour12: false,
    }),
    cameraId: alert.camera_id,
    sector: alert.sector,
    trackId: alert.track_id ?? "UNASSIGNED",
    objectType: alert.type,
    confidence: toPercent(alert.confidence),
    // Phase 8: Use risk_level if available (from risk intelligence engine),
    // otherwise fall back to severity for backward compatibility
    risk: (alert.risk_level ?? alert.severity) as
      | "LOW"
      | "MEDIUM"
      | "HIGH"
      | "CRITICAL",
    riskScore: alert.risk_score,
    eventId: alert.event_id,
    boundaryId: alert.boundary_id,
    status: alert.status === "RESOLVED" ? "RESOLVED" : "ACTIVE",
    description: alert.message,
  };
}

export function detectionToTrack(detection: ApiDetection): TrackRecord {
  return {
    trackId: detection.track_id ?? detection.id,
    objectType: detection.object_type,
    confidence: toPercent(detection.confidence),
    cameraId: detection.camera_id,
    sector: "UNKNOWN SECTOR",
    risk: "LOW",
    firstDetected: new Date(detection.timestamp).toLocaleTimeString([], {
      hour12: false,
    }),
    lastSeen: new Date(detection.timestamp).toLocaleTimeString([], {
      hour12: false,
    }),
    direction: "NOT AVAILABLE",
    speed: "NOT AVAILABLE",
    status: "ACTIVE",
  };
}
