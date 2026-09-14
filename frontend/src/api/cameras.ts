import { apiBaseUrl, apiFetch } from "./client";
import type {
  ApiCamera,
  ApiCameraProcessingStatus,
  ApiCameraRuntimeSummary,
} from "../types/api";

export function getCameras() {
  return apiFetch<ApiCamera[]>("/api/cameras");
}

export function getCamera(cameraId: string) {
  return apiFetch<ApiCamera>(`/api/cameras/${encodeURIComponent(cameraId)}`);
}

export function createCamera(camera: Omit<ApiCamera, "id" | "created_at">) {
  return apiFetch<ApiCamera>("/api/cameras", {
    method: "POST",
    body: JSON.stringify(camera),
  });
}

export function updateCamera(
  cameraId: string,
  camera: Omit<ApiCamera, "id" | "created_at">,
) {
  return apiFetch<ApiCamera>(`/api/cameras/${encodeURIComponent(cameraId)}`, {
    method: "PUT",
    body: JSON.stringify(camera),
  });
}

export function deleteCamera(cameraId: string) {
  return apiFetch<void>(`/api/cameras/${encodeURIComponent(cameraId)}`, {
    method: "DELETE",
  });
}

export function getCameraProcessingStatus(cameraId: string) {
  return apiFetch<ApiCameraProcessingStatus>(
    `/api/cameras/${encodeURIComponent(cameraId)}/status`,
  );
}

export function getCameraRuntimeSummary(cameraId: string) {
  return apiFetch<ApiCameraRuntimeSummary>(
    `/api/cameras/${encodeURIComponent(cameraId)}/summary`,
  );
}

export function getCameraRuntimeSummaries() {
  return apiFetch<ApiCameraRuntimeSummary[]>("/api/cameras/runtime/summaries");
}

export function startCamera(cameraId: string, loop = true) {
  return apiFetch<ApiCameraProcessingStatus>(
    `/api/cameras/${encodeURIComponent(cameraId)}/start`,
    { method: "POST", body: JSON.stringify({ loop }) },
  );
}

export function stopCamera(cameraId: string) {
  return apiFetch<ApiCameraProcessingStatus>(
    `/api/cameras/${encodeURIComponent(cameraId)}/stop`,
    { method: "POST" },
  );
}

export function getCameraStreamUrl(cameraId: string) {
  return `${apiBaseUrl}/api/cameras/${encodeURIComponent(cameraId)}/stream`;
}

export function getProcessedCameraStreamUrl(cameraId: string) {
  return `${apiBaseUrl}/api/cameras/${encodeURIComponent(cameraId)}/processed-stream`;
}
