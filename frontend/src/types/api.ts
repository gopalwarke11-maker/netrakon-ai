export type ApiCameraStatus = "ONLINE" | "OFFLINE" | "MAINTENANCE";
export type ApiAlertSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ApiAlertStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED";
export type ApiRiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ApiBehaviorType =
  | "LOITERING"
  | "STATIONARY"
  | "RAPID_MOVEMENT"
  | "DIRECTION_REVERSAL"
  | "REPEATED_APPROACH"
  | "REPEATED_INTRUSION"
  | "ABNORMAL_MOVEMENT";
export type ApiBehaviorSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface ApiCamera {
  id: string;
  name: string;
  sector: string;
  location: string;
  status: ApiCameraStatus;
  source_type: "FILE" | "RTSP" | "MJPEG" | "DEVICE";
  stream_url: string | null;
  created_at: string;
}

export type ApiCameraRuntimeState =
  | "OFFLINE"
  | "CONNECTING"
  | "RECONNECTING"
  | "ONLINE"
  | "PROCESSING"
  | "ERROR"
  | "STOPPED";

export interface ApiCameraProcessingStatus {
  camera_id: string;
  status: ApiCameraRuntimeState;
  source_type: "FILE" | "RTSP" | "MJPEG" | "DEVICE";
  resolution: string | null;
  fps: number;
  last_frame_time: string | null;
  frames_processed: number;
  detections_count: number;
  active_tracks: number;
  processing_fps: number;
  error: string | null;
  loop_enabled: boolean;
}

export interface ApiTrackedObject {
  track_id: number;
  class_id: number;
  class_name: string;
  confidence: number;
  bounding_box: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    width: number;
    height: number;
  };
  center_x: number;
  center_y: number;
  frame_number?: number | null;
  image_width?: number | null;
  image_height?: number | null;
}

export interface ApiTrackSummary {
  track_id: number;
  class_name: string;
  first_seen_frame: number;
  last_seen_frame: number;
  frames_seen: number;
  latest_center_x: number;
  latest_center_y: number;
  latest_bounding_box: ApiTrackedObject["bounding_box"];
}

export interface ApiCameraRuntimeSummary {
  camera_id: string;
  status: ApiCameraRuntimeState;
  source_type: "FILE" | "RTSP" | "MJPEG" | "DEVICE";
  current_detections: ApiTrackedObject[];
  historical_tracks: ApiTrackSummary[];
  detection_class_counts: Record<string, number>;
  total_detections: number;
  average_confidence: number | null;
  intrusions: Array<Record<string, unknown>>;
  last_frame_time: string | null;
}

export interface ApiBoundary {
  id: string;
  name: string;
  camera_id: string;
  enabled: boolean;
  severity: ApiAlertSeverity;
  point_a: { x: number; y: number };
  point_b: { x: number; y: number };
}

export interface ApiAlert {
  id: string;
  camera_id: string;
  sector: string;
  type: string;
  severity: ApiAlertSeverity;
  message: string;
  track_id: string | null;
  confidence: number | null;
  timestamp: string;
  status: ApiAlertStatus;
  boundary_id?: string | null;
  event_id?: string | null;
  source?: string;
  created_at?: string;
  risk_score?: number;
  risk_level?: ApiRiskLevel;
}

export interface RiskFactor {
  factor: string;
  value: string;
  contribution: number;
  reason: string;
}

export interface ApiRiskAssessment {
  risk_score: number;
  risk_level: ApiRiskLevel;
  factors: RiskFactor[];
  assessed_at: string;
  intrusion_event_id: string;
  camera_id: string | null;
  boundary_id: string | null;
  track_id: number;
}

export interface BehaviorObservation {
  behavior_type: ApiBehaviorType;
  severity: ApiBehaviorSeverity;
  confidence: number;
  duration_seconds: number | null;
  evidence: Record<string, number | string>;
  reason: string;
  detected_at: string;
}

export interface ApiBehaviorAssessment {
  id: string;
  camera_id: string;
  track_id: number;
  observations: BehaviorObservation[];
  behavior_score: number;
  primary_behavior: ApiBehaviorType | null;
  assessed_at: string;
  duration_window_seconds: number;
  intrusion_event_id: string | null;
  created_at: string;
}

export interface IntrusionWebSocketEvent {
  type: "intrusion";
  event_id: string;
  alert_id: string;
  timestamp: string;
  camera_id: string;
  boundary_id: string;
  boundary_name: string;
  track_id: string;
  severity: ApiAlertSeverity;
  direction: string;
  object_class: string;
  confidence: number | null;
  message: string;
  sector: string;
  status: ApiAlertStatus;
  risk_score?: number;
  risk_level?: ApiRiskLevel;
  behavior_score?: number;
  primary_behavior?: ApiBehaviorType;
}

export interface ApiBoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ApiDetection {
  id: string;
  camera_id: string;
  object_type: string;
  confidence: number;
  track_id: string | null;
  bounding_box: ApiBoundingBox;
  timestamp: string;
}

export interface ApiHealth {
  status: string;
  service: string;
  version: string;
  environment: string;
}
