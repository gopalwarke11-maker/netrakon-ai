import { create } from "zustand";

export type CameraViewMode = "grid" | "fullscreen";

interface CameraState {
  selectedCamera: string;
  detectionEnabled: boolean;
  trackingEnabled: boolean;
  recording: boolean;
  viewMode: CameraViewMode;
  setSelectedCamera: (cameraId: string) => void;
  toggleDetection: () => void;
  toggleTracking: () => void;
  toggleRecording: () => void;
  setViewMode: (viewMode: CameraViewMode) => void;
}

export const useCameraStore = create<CameraState>((set) => ({
  selectedCamera: "CAM-01",
  detectionEnabled: true,
  trackingEnabled: false,
  recording: false,
  viewMode: "grid",
  setSelectedCamera: (selectedCamera) => set({ selectedCamera }),
  toggleDetection: () =>
    set((state) => ({ detectionEnabled: !state.detectionEnabled })),
  toggleTracking: () =>
    set((state) => ({ trackingEnabled: !state.trackingEnabled })),
  toggleRecording: () => set((state) => ({ recording: !state.recording })),
  setViewMode: (viewMode) => set({ viewMode }),
}));
