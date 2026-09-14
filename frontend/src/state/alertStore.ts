import { create } from "zustand";

interface AlertState {
  resolvedAlertIds: string[];
  connectionStatus: "CONNECTING" | "CONNECTED" | "DISCONNECTED";
  resolveAlert: (alertId: string) => void;
  setConnectionStatus: (status: AlertState["connectionStatus"]) => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  resolvedAlertIds: [],
  connectionStatus: "DISCONNECTED",
  resolveAlert: (alertId) =>
    set((state) => ({
      resolvedAlertIds: state.resolvedAlertIds.includes(alertId)
        ? state.resolvedAlertIds
        : [...state.resolvedAlertIds, alertId],
    })),
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
}));
