import { useQueries, useQuery } from "@tanstack/react-query";
import { getAlerts, getCameraBehaviors } from "./alerts";
import {
  getCameraProcessingStatus,
  getCameraRuntimeSummary,
  getCameraRuntimeSummaries,
  getCameras,
} from "./cameras";
import { getBoundaries } from "./boundaries";
import { getDetections } from "./detections";
import { getHealth } from "./health";

export function useBackendHealth() {
  return useQuery({
    queryKey: ["backend", "health"],
    queryFn: getHealth,
    retry: false,
    refetchInterval: 30000,
  });
}

export function useCameras() {
  return useQuery({ queryKey: ["cameras"], queryFn: getCameras, retry: 1 });
}

export function useCameraProcessingStatus(cameraId: string) {
  return useQuery({
    queryKey: ["cameras", cameraId, "processing"],
    queryFn: () => getCameraProcessingStatus(cameraId),
    retry: false,
    refetchInterval: 1000,
  });
}

export function useCameraProcessingStatuses(cameraIds: string[]) {
  return useQueries({
    queries: cameraIds.map((cameraId) => ({
      queryKey: ["cameras", cameraId, "processing"],
      queryFn: () => getCameraProcessingStatus(cameraId),
      retry: false,
      refetchInterval: 5000,
    })),
  });
}

export function useCameraBehaviors(cameraId: string) {
  return useQuery({
    queryKey: ["behaviors", cameraId],
    queryFn: () => getCameraBehaviors(cameraId, 1),
    retry: false,
    refetchInterval: 5000,
  });
}

export function useCameraRuntimeSummary(cameraId: string) {
  return useQuery({
    queryKey: ["cameras", cameraId, "summary"],
    queryFn: () => getCameraRuntimeSummary(cameraId),
    retry: false,
    refetchInterval: 1000,
  });
}

export function useCameraRuntimeSummaries() {
  return useQuery({
    queryKey: ["cameras", "runtime", "summaries"],
    queryFn: getCameraRuntimeSummaries,
    retry: false,
    refetchInterval: 5000,
  });
}

export function useBoundaries() {
  return useQuery({
    queryKey: ["boundaries"],
    queryFn: getBoundaries,
    retry: 1,
    refetchInterval: 10000,
  });
}

export function useAlerts() {
  return useQuery({ queryKey: ["alerts"], queryFn: getAlerts, retry: 1 });
}

export function useDetections() {
  return useQuery({
    queryKey: ["detections"],
    queryFn: getDetections,
    retry: 1,
  });
}
