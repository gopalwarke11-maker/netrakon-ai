import { create } from "zustand";

interface SettingsState {
  detectionEnabled: boolean;
  trackingEnabled: boolean;
  recording: boolean;
  alertSound: boolean;
  darkMode: boolean;
  highRiskAlerts: boolean;
  notificationDisplay: boolean;
  autoReconnect: boolean;
  compactMode: boolean;
  animations: boolean;
  fullscreen: boolean;
  confidenceThreshold: number;
  defaultCamera: string;
  setConfidenceThreshold: (threshold: number) => void;
  setDefaultCamera: (cameraId: string) => void;
  toggleSetting: (
    setting:
      | "detectionEnabled" | "trackingEnabled" | "recording" | "alertSound" | "darkMode"
      | "highRiskAlerts" | "notificationDisplay" | "autoReconnect" | "compactMode" | "animations" | "fullscreen",
  ) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  detectionEnabled: true,
  trackingEnabled: false,
  recording: false,
  alertSound: true,
  darkMode: true,
  highRiskAlerts: true,
  notificationDisplay: true,
  autoReconnect: true,
  compactMode: false,
  animations: false,
  fullscreen: false,
  confidenceThreshold: 70,
  defaultCamera: "CAM-01",
  setConfidenceThreshold: (confidenceThreshold) => set({ confidenceThreshold }),
  setDefaultCamera: (defaultCamera) => set({ defaultCamera }),
  toggleSetting: (setting) => set((state) => ({ [setting]: !state[setting] })),
}));
