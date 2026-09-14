import { create } from "zustand";

interface DetectionState {
  selectedTrackId: string;
  setSelectedTrack: (trackId: string) => void;
}

export const useDetectionStore = create<DetectionState>((set) => ({
  selectedTrackId: "T-1042",
  setSelectedTrack: (selectedTrackId) => set({ selectedTrackId }),
}));
