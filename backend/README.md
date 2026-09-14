# NETRAKON AI Backend

Phase 4 FastAPI backend with **real YOLO object detection** (Phase 3) and
**ByteTrack object tracking** (Phase 4), powered by [Ultralytics YOLOv8](https://docs.ultralytics.com/).

PostgreSQL is the persistent source of truth for cameras, boundaries, alerts,
and intrusion-event history. WebSocket delivery is real-time only and does not
replace REST history.

---

## Setup

From `backend/`:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Install PostgreSQL, create a database named `netrakon`, and replace
`YOUR_PASSWORD` in `.env` with the local credentials. Do not commit `.env`.
The application fails clearly at startup when `DATABASE_URL` is absent or the
database cannot be reached; it never falls back to in-memory persistence.

The API runs at `http://127.0.0.1:8000`.
Interactive documentation: [`/docs`](http://127.0.0.1:8000/docs) · [`/redoc`](http://127.0.0.1:8000/redoc).

---

## AI Model & Tracker

| Setting       | Value                                  |
| ------------- | -------------------------------------- |
| Framework     | Ultralytics YOLOv8                     |
| Default model | `yolov8n.pt` (nano, ~6 MB)             |
| Dataset       | COCO (80 classes)                      |
| Tracker       | ByteTrack (bundled with `ultralytics`) |
| Device        | CPU (CUDA auto-detected if available)  |

Ultralytics downloads model weights automatically on first startup.
ByteTrack requires **no extra installation** — it is bundled with `ultralytics`.

To use a larger model, set in `.env`:

```
YOLO_MODEL_NAME=yolov8s.pt
```

---

## Endpoints

### Real-time alerts (Phase 6)

`WS /ws/alerts` is a server-to-client stream for confirmed intrusion events.
On connection it sends `{ "type": "connected" }`; intrusions include `event_id`,
`alert_id`, timestamp, camera/boundary/track IDs, severity, direction, object
metadata, and the existing alert message. `GET /api/alerts` remains the source
for current/history data. Clients should reconnect after unexpected disconnects.

### Health & General

| Method | Path          | Description                         |
| ------ | ------------- | ----------------------------------- |
| `GET`  | `/api/health` | Service health check                |
| `GET`  | `/api/ready`  | PostgreSQL and YOLO readiness check |

### Cameras

| Method   | Path                | Description    |
| -------- | ------------------- | -------------- |
| `GET`    | `/api/cameras`      | List cameras   |
| `POST`   | `/api/cameras`      | Create camera  |
| `GET`    | `/api/cameras/{id}` | Get camera     |
| `PUT`    | `/api/cameras/{id}` | Replace camera |
| `DELETE` | `/api/cameras/{id}` | Delete camera  |

### Camera Processing (Phase 11)

The camera processing service manages one worker per registered camera. It uses
the existing low-light processor and `TrackSession` pipeline, while creating an
isolated YOLO instance and track history for each camera. Sources are local
video files, RTSP URLs, or OpenCV device IDs.

| Method | Path                        | Description                            |
| ------ | --------------------------- | -------------------------------------- |
| `POST` | `/api/cameras/{id}/start`   | Validate and start processing          |
| `POST` | `/api/cameras/{id}/stop`    | Stop processing and release the source |
| `POST` | `/api/cameras/{id}/restart` | Reset transient state and restart      |
| `GET`  | `/api/cameras/{id}/status`  | Read camera-scoped runtime metrics     |
| `GET`  | `/api/cameras/runtime`      | List registered runtime statuses       |

Runtime status includes source type, resolution, FPS, processed frames,
detection count, active tracks, processing FPS, last frame time, and errors.
Stopping or restarting one camera does not reset another camera. Confirmed
intrusions continue to use the existing camera-scoped persistence and
`/ws/alerts` payloads.

After tracking, each camera worker invokes the existing Phase 9 behavior engine
with its own `(camera_id, track_id)` history. Meaningful assessments are
deduplicated per behavior state, persisted through `BehaviorService` to
`behavior_observations`, and published as backward-compatible
`type: "behavior"` messages on `/ws/alerts`. Behavior scoring remains unchanged.

Phase 12 deterministic E2E and reliability checks are available with:

```powershell
python -m pytest -q test_phase12_e2e.py
python measure_phase12_e2e.py
```

`measure_phase12_e2e.py` is explicitly a **Deterministic pipeline orchestration
benchmark**. It uses an injected tracker and reports unavailable YOLO,
persistence, WebSocket, and event-latency timings as `NOT MEASURED`. It does
not represent production FPS or scalability and does not validate physical RTSP
hardware.

Phase 13 real local-video validation utilities:

```powershell
python inspect_phase13_videos.py validation_input/YOUR_NIGHT_VIDEO.mp4 validation_input/night_test.mp4
python validate_phase13_video.py --video validation_input/YOUR_NIGHT_VIDEO.mp4 --camera-id CAM-01 --enhance-low-light --output-json validation_output/phase13_cam01.json
python measure_phase13_real_video.py
```

Results are recorded in the root `PHASE13_REAL_WORLD_VALIDATION_REPORT.md`.
The available `night_test.mp4` is real security footage but is classified as
not suitable for night validation by the existing luminance threshold.

### Alerts

| Method  | Path               | Description  |
| ------- | ------------------ | ------------ |
| `GET`   | `/api/alerts`      | List alerts  |
| `POST`  | `/api/alerts`      | Create alert |
| `GET`   | `/api/alerts/{id}` | Get alert    |
| `PATCH` | `/api/alerts/{id}` | Update alert |

### Detections (in-memory store)

| Method | Path                   | Description            |
| ------ | ---------------------- | ---------------------- |
| `GET`  | `/api/detections`      | List stored detections |
| `POST` | `/api/detections`      | Store a detection      |
| `GET`  | `/api/detections/{id}` | Get stored detection   |

### 🤖 AI Detection (Phase 3)

| Method | Path             | Description                   |
| ------ | ---------------- | ----------------------------- |
| `POST` | `/api/ai/detect` | Run YOLO on an uploaded image |

### 🎯 AI Tracking (Phase 4 — new)

| Method | Path            | Description                               |
| ------ | --------------- | ----------------------------------------- |
| `POST` | `/api/ai/track` | Run YOLO + ByteTrack on an uploaded video |

---

## Testing AI Detection (Phase 3)

```powershell
# Auto-downloads a Pexels sample image
python test_detection.py

# Use your own image
python test_detection.py C:\path\to\image.jpg

# With confidence override
python test_detection.py image.jpg --conf 0.4
```

---

## Testing AI Tracking (Phase 4)

```powershell
# Auto-generates a synthetic test video (no download needed)
python test_tracking.py

# Use your own video file
python test_tracking.py C:\path\to\video.mp4

# Process only the first 30 frames (fast dev test)
python test_tracking.py --max-frames 30

# Full options
python test_tracking.py video.mp4 --conf 0.3 --max-frames 60
```

### Manual test via curl

```powershell
curl -X POST "http://127.0.0.1:8000/api/ai/track?conf=0.25&max_frames=60" `
  -F "file=@video.mp4" `
  -H "Accept: application/json"
```

---

## Example Tracking Response

```json
{
  "filename": "video.mp4",
  "total_frames_in_video": 300,
  "total_frames_processed": 60,
  "tracks": [
    {
      "track_id": 1,
      "class_name": "person",
      "first_seen_frame": 1,
      "last_seen_frame": 58,
      "frames_seen": 52,
      "latest_center_x": 342.5,
      "latest_center_y": 287.0,
      "latest_bounding_box": {
        "x1": 210.0,
        "y1": 140.0,
        "x2": 475.0,
        "y2": 434.0,
        "width": 265.0,
        "height": 294.0
      }
    },
    {
      "track_id": 2,
      "class_name": "car",
      "first_seen_frame": 5,
      "last_seen_frame": 60,
      "frames_seen": 48,
      "latest_center_x": 620.1,
      "latest_center_y": 390.8,
      "latest_bounding_box": {
        "x1": 510.0,
        "y1": 300.0,
        "x2": 730.0,
        "y2": 481.6,
        "width": 220.0,
        "height": 181.6
      }
    }
  ],
  "total_processing_time_ms": 4821.5,
  "avg_frame_time_ms": 80.4,
  "estimated_fps": 12.44,
  "model_name": "yolov8n.pt",
  "tracker": "bytetrack"
}
```

---

## Architecture

```
app/
├── ai/
│   ├── __init__.py             AI module package
│   ├── model_manager.py        Singleton YOLO loader (warm-up at startup)
│   ├── detector.py             Phase 3: image bytes → DetectResponse
│   ├── schemas.py              All AI Pydantic schemas (detection + tracking)
│   ├── tracker.py              Phase 4: TrackSession — per-frame ByteTrack
│   └── track_history.py        Phase 4: bounded per-track memory
│
├── services/
│   └── camera_processor.py     Phase 11: source, worker, and manager lifecycle
│
├── api/routes/
│   ├── health.py               GET  /api/health
│   ├── cameras.py              CRUD /api/cameras
│   ├── alerts.py               CRUD /api/alerts
│   ├── detections.py           CRUD /api/detections  (in-memory store)
│   ├── ai_detect.py            POST /api/ai/detect   (Phase 3)
│   └── ai_track.py             POST /api/ai/track    (Phase 4)
│
├── core/
│   └── config.py               Centralized settings
│
├── models/                     Phase 1/2 Pydantic schemas
└── services/                   Database-backed application services
```

**Tracking flow:**

```
POST /api/ai/track (multipart video)
        ↓
  ai_track.py  (route — saves to temp file, opens with OpenCV)
        ↓
  TrackSession.process_frame()  (per frame loop)
        ↓
  model.track(..., persist=True)  ← ByteTrack, persistent IDs
        ↓
  TrackHistory.update()  (bounded position log)
        ↓
  TrackResponse (JSON summary)
```

---

## Environment Variables

| Variable                       | Default          | Description                               |
| ------------------------------ | ---------------- | ----------------------------------------- |
| `YOLO_MODEL_NAME`              | `yolov8n.pt`     | Ultralytics model name or local path      |
| `YOLO_CONF_THRESHOLD`          | `0.25`           | Default detection confidence              |
| `YOLO_TRACKER`                 | `bytetrack.yaml` | Tracker config (bundled with ultralytics) |
| `TRACK_CONF_THRESHOLD`         | `0.25`           | Default tracking confidence               |
| `TRACK_POSITION_HISTORY_LIMIT` | `50`             | Max position entries per track            |
| `TRACK_MAX_VIDEO_SIZE_MB`      | `200`            | Max accepted video upload size            |
| `HOST`                         | `127.0.0.1`      | Uvicorn bind address                      |
| `PORT`                         | `8000`           | Uvicorn port                              |

---

## Known Limitations (by design)

| Feature                                  | Status      |
| ---------------------------------------- | ----------- |
| RTSP / live camera streaming             | ❌ Phase 5  |
| WebSocket real-time output               | ❌ Phase 5  |
| PostgreSQL persistence                   | ✅ Phase 7  |
| Intrusion detection / virtual boundaries | ✅ Phase 5  |
| Behaviour / loitering analysis           | ❌ Phase 5+ |
| Authentication                           | ❌ Phase 5+ |
| Multi-camera orchestration               | ❌ Phase 5+ |
| Custom model training                    | ❌ Phase 5+ |

---

## Phase 5: Virtual Security Boundaries and Intrusion Detection

Phase 5 evaluates ByteTrack objects against one or more camera-specific virtual
line boundaries. Boundary configuration and confirmed events persist in
PostgreSQL across backend restarts.

Each boundary has an `id`, `camera_id`, name, enabled flag, points `point_a`
and `point_b`, `restricted_side`, severity, and a pixel `tolerance`. Coordinates
are image pixels with `(0, 0)` at the top-left; X increases right and Y increases
down. `restricted_side: "positive"` means points whose orientation is greater
than zero are restricted; `"negative"` means less than zero is restricted.

The geometry is slope-free and supports horizontal, vertical, and diagonal
lines:

```
orientation(A, B, P) = (Bx - Ax) * (Py - Ay) - (By - Ay) * (Px - Ax)
```

Objects are evaluated using the bounding-box bottom-center anchor:
`((x1 + x2) / 2, y2)`. An intrusion is emitted only for an
unrestricted-to-restricted crossing. A tolerance dead-zone suppresses line
touches and detector jitter. State is scoped to `(camera_id, boundary_id,
track_id)` and prevents duplicate alerts while an object remains inside.

Intrusions create ordinary alert records with `type: INTRUSION`; severity is
deterministic: boundary severity for people/default objects, `CRITICAL` for
vehicles, and `LOW` for common animals.

### Phase 5 API

| Endpoint                                       | Purpose                                                    |
| ---------------------------------------------- | ---------------------------------------------------------- |
| `GET/POST /api/boundaries`                     | List or create boundaries                                  |
| `GET/PUT/DELETE /api/boundaries/{boundary_id}` | Read, update, or delete a boundary                         |
| `GET /api/cameras/{camera_id}/boundaries`      | Camera-specific boundaries                                 |
| `POST /api/ai/intrusion-test`                  | Deterministic **synthetic simulation**, not YOLO inference |
| `POST /api/ai/track?camera_id=CAM-01`          | Run YOLO + ByteTrack and evaluate that camera's boundaries |

### Tests

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest -q
```

The suite covers horizontal, vertical, and diagonal geometry, both restricted
sides, touching/jitter suppression, duplicate prevention, state isolation,
CRUD validation, and Phase 3/4 regression checks. Real-world validation still
requires a suitable video containing actual tracked people or vehicles.

## Phase 7 Persistence

Persistent entities are stored in PostgreSQL: cameras, virtual boundaries,
alerts, and confirmed intrusion events. Use `alembic upgrade head` before the
first run. `GET /api/intrusions` supports bounded history queries with
`camera_id`, `boundary_id`, `severity`, `start_time`, `end_time`, `limit`, and
`offset` filters. The default limit is 100 and the maximum is 500.

An intrusion is committed atomically with its alert before it is sent through
`/ws/alerts`. YOLO and ByteTrack processing remains separate from high-volume
frame persistence, and no frames are written to PostgreSQL.
