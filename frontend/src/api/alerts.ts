import { apiFetch } from "./client";
import type {
  ApiAlert,
  ApiAlertStatus,
  ApiRiskAssessment,
  ApiBehaviorAssessment,
} from "../types/api";

export function getAlerts() {
  return apiFetch<ApiAlert[]>("/api/alerts");
}

export function getAlert(alertId: string) {
  return apiFetch<ApiAlert>(`/api/alerts/${encodeURIComponent(alertId)}`);
}

export function createAlert(alert: Omit<ApiAlert, "id">) {
  return apiFetch<ApiAlert>("/api/alerts", {
    method: "POST",
    body: JSON.stringify(alert),
  });
}

export function updateAlert(
  alertId: string,
  update: { status?: ApiAlertStatus; message?: string },
) {
  return apiFetch<ApiAlert>(`/api/alerts/${encodeURIComponent(alertId)}`, {
    method: "PATCH",
    body: JSON.stringify(update),
  });
}

// Phase 8: Risk Intelligence
export function getRiskAssessment(eventId: string) {
  return apiFetch<ApiRiskAssessment>(
    `/api/ai/risk/${encodeURIComponent(eventId)}`,
  );
}

// Phase 9: Behavior Analysis
export function getBehaviorAssessment(behaviorId: string) {
  return apiFetch<ApiBehaviorAssessment>(
    `/api/ai/behavior/${encodeURIComponent(behaviorId)}`,
  );
}

export function getTrackBehaviors(cameraId: string, trackId: number) {
  return apiFetch<ApiBehaviorAssessment[]>(
    `/api/ai/behavior/track/${encodeURIComponent(cameraId)}/${trackId}`,
  );
}

export function getCameraBehaviors(cameraId: string, limit = 100) {
  return apiFetch<ApiBehaviorAssessment[]>(
    `/api/ai/behavior/camera/${encodeURIComponent(cameraId)}?limit=${limit}`,
  );
}
