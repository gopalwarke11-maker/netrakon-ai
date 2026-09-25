import { apiBaseUrl, apiFetch } from "./client";
import type {
  ApiCamera,
  ApiCameraProcessingStatus,
  ApiCameraRuntimeSummary,
  ApiCameraTestRequest,
  ApiCameraTestResponse,
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

export interface CloudinaryUploadResponse {
  secure_url: string;
  public_id: string;
  original_filename?: string;
  bytes?: number;
  duration?: number;
  format?: string;
  resource_type?: string;
}

export async function uploadVideoToCloudinary(
  file: File,
): Promise<CloudinaryUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("upload_preset", "netrakon_videos");

  const url = "https://api.cloudinary.com/v1_1/sbso5zkn/video/upload";

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new Error("Failed to connect to Cloudinary upload service.");
  }

  if (!response.ok) {
    let errorMessage = `Cloudinary upload failed with status ${response.status}`;
    try {
      const errorData = (await response.json()) as { error?: { message?: string } };
      if (errorData?.error?.message) {
        errorMessage = `Cloudinary upload error: ${errorData.error.message}`;
      }
    } catch {
      /* fallback to status text */
    }
    throw new Error(errorMessage);
  }

  const data = (await response.json()) as CloudinaryUploadResponse;

  if (!data.secure_url || typeof data.secure_url !== "string") {
    throw new Error("Cloudinary response missing valid secure_url.");
  }

  if (!data.secure_url.startsWith("https://")) {
    throw new Error("Cloudinary returned a non-HTTPS secure_url.");
  }

  return data;
}

export function uploadCameraVideo(
  file: File,
  details: {
    name?: string;
    sector?: string;
    location?: string;
    cameraId?: string;
  } = {},
) {
  const formData = new FormData();
  formData.append("file", file);
  if (details.name) formData.append("name", details.name);
  if (details.sector) formData.append("sector", details.sector);
  if (details.location) formData.append("location", details.location);
  if (details.cameraId) formData.append("camera_id", details.cameraId);

  return apiFetch<ApiCamera>("/api/cameras/upload", {
    method: "POST",
    body: formData,
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
