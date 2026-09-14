import { apiBaseUrl } from "./client";
import type {
  ApiAlert,
  ApiBehaviorType,
  IntrusionWebSocketEvent,
} from "../types/api";

export type AlertStreamStatus = "CONNECTING" | "CONNECTED" | "DISCONNECTED";

export function getAlertWebSocketUrl() {
  const configured = import.meta.env.VITE_ALERT_WS_URL as string | undefined;
  if (configured) return configured;
  const url = new URL(apiBaseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/alerts";
  url.search = "";
  return url.toString();
}

export function parseIntrusionEvent(
  value: unknown,
): IntrusionWebSocketEvent | null {
  if (!value || typeof value !== "object") return null;
  const event = value as Record<string, unknown>;
  const required = [
    "event_id",
    "alert_id",
    "timestamp",
    "camera_id",
    "boundary_id",
    "track_id",
    "severity",
    "direction",
    "object_class",
    "message",
    "sector",
    "status",
  ];
  if (
    event.type !== "intrusion" ||
    required.some((key) => typeof event[key] !== "string")
  )
    return null;
  if (event.confidence !== null && typeof event.confidence !== "number")
    return null;
  return event as unknown as IntrusionWebSocketEvent;
}

export function intrusionEventToAlert(
  event: IntrusionWebSocketEvent,
): ApiAlert {
  return {
    id: event.alert_id,
    camera_id: event.camera_id,
    sector: event.sector,
    type: "INTRUSION",
    severity: event.severity,
    message: event.message,
    track_id: event.track_id,
    confidence: event.confidence,
    timestamp: event.timestamp,
    status: event.status,
    risk_score: event.risk_score,
    risk_level: event.risk_level,
  };
}

export interface BehaviorWebSocketEvent {
  type: "behavior";
  behavior_id: string;
  camera_id: string;
  track_id: string;
  behavior_type: ApiBehaviorType | null;
  behavior_score: number;
}

export function parseBehaviorEvent(
  value: unknown,
): BehaviorWebSocketEvent | null {
  if (!value || typeof value !== "object") return null;
  const event = value as Record<string, unknown>;
  if (event.type !== "behavior") return null;
  if (
    typeof event.behavior_id !== "string" ||
    typeof event.camera_id !== "string"
  )
    return null;
  if (
    typeof event.track_id !== "string" ||
    typeof event.behavior_score !== "number"
  )
    return null;
  return event as unknown as BehaviorWebSocketEvent;
}
