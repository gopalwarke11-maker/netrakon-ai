import { apiFetch } from "./client";
import type { ApiDetection } from "../types/api";

export function getDetections() {
  return apiFetch<ApiDetection[]>("/api/detections");
}

export function getDetection(detectionId: string) {
  return apiFetch<ApiDetection>(
    `/api/detections/${encodeURIComponent(detectionId)}`,
  );
}

export function createDetection(detection: Omit<ApiDetection, "id">) {
  return apiFetch<ApiDetection>("/api/detections", {
    method: "POST",
    body: JSON.stringify(detection),
  });
}
