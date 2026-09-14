export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface CameraRecord {
  cameraId: string;
  name?: string;
  sector: string;
  location?: string;
  status?: string;
  sourceType?: string;
  streamUrl?: string | null;
  showDetection: boolean;
  detection?: {
    label: string;
    confidence: number;
    trackId: string;
    risk: RiskLevel;
  };
}

export interface AlertRecord {
  id: string;
  timestamp: string;
  cameraId: string;
  sector: string;
  trackId: string;
  objectType: string;
  confidence: number;
  risk: RiskLevel;
  riskScore?: number;
  eventId?: string | null;
  boundaryId?: string | null;
  status: "ACTIVE" | "RESOLVED";
  description: string;
}

export interface TrackRecord {
  trackId: string;
  objectType: string;
  confidence: number;
  cameraId: string;
  sector: string;
  risk: RiskLevel;
  firstDetected: string;
  lastSeen: string;
  direction: string;
  speed: string;
  status: "ACTIVE" | "LOST";
}

export interface SectorRecord {
  id: string;
  name: string;
  risk: RiskLevel;
  cameras: string[];
  activeTracks: number;
  latestDetection: string;
  confidence: number;
}

export const cameras: CameraRecord[] = [
  {
    cameraId: "CAM-01",
    sector: "SECTOR 1",
    showDetection: true,
    detection: {
      label: "PERSON",
      confidence: 91,
      trackId: "T-1001",
      risk: "LOW",
    },
  },
  { cameraId: "CAM-02", sector: "SECTOR 2", showDetection: false },
  {
    cameraId: "CAM-03",
    sector: "SECTOR 3",
    showDetection: true,
    detection: {
      label: "PERSON",
      confidence: 89,
      trackId: "T-1021",
      risk: "MEDIUM",
    },
  },
  {
    cameraId: "CAM-04",
    sector: "SECTOR 4",
    showDetection: true,
    detection: {
      label: "PERSON",
      confidence: 94,
      trackId: "T-1042",
      risk: "HIGH",
    },
  },
];

export const alerts: AlertRecord[] = [
  {
    id: "ALT-2048",
    timestamp: "14:32:08",
    cameraId: "CAM-04",
    sector: "SECTOR 4",
    trackId: "T-1042",
    objectType: "PERSON",
    confidence: 94,
    risk: "HIGH",
    status: "ACTIVE",
    description: "Movement detected inside the restricted buffer after hours.",
  },
  {
    id: "ALT-2047",
    timestamp: "14:28:41",
    cameraId: "CAM-03",
    sector: "SECTOR 3",
    trackId: "T-1021",
    objectType: "PERSON",
    confidence: 87,
    risk: "MEDIUM",
    status: "ACTIVE",
    description: "Subject moving toward the northern patrol route.",
  },
  {
    id: "ALT-2046",
    timestamp: "14:19:16",
    cameraId: "CAM-01",
    sector: "SECTOR 1",
    trackId: "T-1001",
    objectType: "PERSON",
    confidence: 72,
    risk: "LOW",
    status: "RESOLVED",
    description:
      "Stationary presence detected beyond the configured threshold.",
  },
  {
    id: "ALT-2045",
    timestamp: "13:57:03",
    cameraId: "CAM-02",
    sector: "SECTOR 2",
    trackId: "T-0998",
    objectType: "VEHICLE",
    confidence: 84,
    risk: "MEDIUM",
    status: "RESOLVED",
    description: "Vehicle paused near an authorized service access point.",
  },
];

export const tracks: TrackRecord[] = [
  {
    trackId: "T-1042",
    objectType: "PERSON",
    confidence: 94,
    cameraId: "CAM-04",
    sector: "SECTOR 4",
    risk: "HIGH",
    firstDetected: "14:30:21",
    lastSeen: "14:32:08",
    direction: "NORTH-EAST",
    speed: "4.2 km/h",
    status: "ACTIVE",
  },
  {
    trackId: "T-1021",
    objectType: "PERSON",
    confidence: 87,
    cameraId: "CAM-03",
    sector: "SECTOR 3",
    risk: "MEDIUM",
    firstDetected: "14:22:05",
    lastSeen: "14:31:44",
    direction: "NORTH",
    speed: "2.8 km/h",
    status: "ACTIVE",
  },
  {
    trackId: "T-1001",
    objectType: "PERSON",
    confidence: 72,
    cameraId: "CAM-01",
    sector: "SECTOR 1",
    risk: "LOW",
    firstDetected: "14:12:43",
    lastSeen: "14:25:19",
    direction: "WEST",
    speed: "1.1 km/h",
    status: "ACTIVE",
  },
];

export const sectors: SectorRecord[] = [
  {
    id: "S1",
    name: "SECTOR 1",
    risk: "LOW",
    cameras: ["CAM-01"],
    activeTracks: 1,
    latestDetection: "PERSON",
    confidence: 72,
  },
  {
    id: "S2",
    name: "SECTOR 2",
    risk: "MEDIUM",
    cameras: ["CAM-02"],
    activeTracks: 0,
    latestDetection: "VEHICLE",
    confidence: 84,
  },
  {
    id: "S3",
    name: "SECTOR 3",
    risk: "MEDIUM",
    cameras: ["CAM-03"],
    activeTracks: 1,
    latestDetection: "PERSON",
    confidence: 87,
  },
  {
    id: "S4",
    name: "SECTOR 4",
    risk: "HIGH",
    cameras: ["CAM-04"],
    activeTracks: 3,
    latestDetection: "PERSON",
    confidence: 94,
  },
];

export const detectionTrend = [34, 48, 42, 67, 58, 76, 64, 91, 83, 98, 88, 104];
export const sectorActivity = [4, 7, 5, 12];
