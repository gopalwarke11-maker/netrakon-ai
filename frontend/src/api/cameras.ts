import { apiBaseUrl, apiFetch } from "./client";
import type {
  ApiCamera,
  ApiCameraProcessingStatus,
  ApiCameraRuntimeSummary,
  ApiCameraTestRequest,
  ApiCameraTestResponse,
  ApiConfirmUploadRequest,
  ApiPresignedUploadRequest,
  ApiPresignedUploadResponse,
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

export function getPresignedUploadUrl(payload: ApiPresignedUploadRequest) {
  return apiFetch<ApiPresignedUploadResponse>(
    "/api/cameras/presigned-upload-url",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function uploadFileToPresignedUrl(
  uploadUrl: string,
  file: File,
  headers: Record<string, string> = {},
) {
  const targetUrl = uploadUrl.startsWith("/")
    ? `${apiBaseUrl}${uploadUrl}`
    : uploadUrl;
  const response = await fetch(targetUrl, {
    method: "PUT",
    headers: {
      "Content-Type": file.type || "video/mp4",
      ...headers,
    },
    body: file,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Direct video upload failed (${response.status}): ${errorText || response.statusText}`,
    );
  }
}

export function confirmUpload(payload: ApiConfirmUploadRequest) {
  return apiFetch<ApiCamera>("/api/cameras/confirm-upload", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function testCameraConnection(payload: ApiCameraTestRequest) {
  return apiFetch<ApiCameraTestResponse>("/api/cameras/test-connection", {
    method: "POST",
    body: JSON.stringify(payload),
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
