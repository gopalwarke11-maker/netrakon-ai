# NETRAKON AI

NETRAKON AI is an AI-powered border surveillance and monitoring system. The repository is organized as two independent applications:

```text
netrakon-ai/
├── frontend/   React + TypeScript + Vite application
└── backend/    FastAPI application and PostgreSQL persistence
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

The frontend uses the REST API for current data and `ws://127.0.0.1:8000/ws/alerts`
for real-time confirmed intrusion delivery. The WebSocket URL is derived from
`VITE_API_BASE_URL` (or can be overridden with `VITE_ALERT_WS_URL`), reconnects
with bounded backoff, and does not replace REST alert retrieval.

## Backend

```powershell
cd backend
venv\Scripts\activate
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Install PostgreSQL, create the `netrakon` database, and set
`DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/netrakon`
in `backend/.env`. Replace the placeholder password locally and never commit
the `.env` file.

The API runs at `http://127.0.0.1:8000`. OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

Health endpoints:

- `GET /api/health` reports process health.
- `GET /api/ready` checks PostgreSQL and YOLO readiness and returns `503` when a critical dependency is unavailable.

## Current Scope

PostgreSQL is the persistent source of truth for cameras, boundaries, alerts,
and intrusion-event history. `GET /api/intrusions` provides bounded, filtered
history with `limit` and `offset`. `/ws/alerts` delivers newly confirmed,
already-persisted intrusions in real time; it does not replace REST history.
YOLO and ByteTrack processing remains separate from high-volume frame storage.
Detections and tracking frames are not written to PostgreSQL.

## Multi-Camera Processing (Phase 11)

Camera processing is keyed by `camera_id`. Each active camera owns its source,
worker, YOLO model instance, ByteTrack session, track history, and runtime
metrics. Live behavior analysis consumes each camera's track history and
persists deduplicated observations through the existing
`behavior_observations` table. Supported sources are local video files, RTSP
URLs, and OpenCV camera devices. Numeric track IDs may repeat between cameras,
but application state and events remain camera-scoped.

Lifecycle endpoints:

- `POST /api/cameras/{camera_id}/start`
- `POST /api/cameras/{camera_id}/stop`
- `POST /api/cameras/{camera_id}/restart`
- `GET /api/cameras/{camera_id}/status`
- `GET /api/cameras/runtime`

Local synthetic videos can exercise the worker without RTSP hardware:

```powershell
cd backend
python -m pytest -q test_phase11_multicamera.py
```

The local worker architecture is intended for functional multi-camera
processing. It does not claim production scalability or real RTSP validation.

Phase 12 also validates actual application-process restart persistence and
database-backed behavior idempotency. Browser-runtime E2E and physical RTSP
hardware remain untested; deterministic local validation is used instead.

Phase 13 real local-video validation is documented in
[PHASE13_REAL_WORLD_VALIDATION_REPORT.md](PHASE13_REAL_WORLD_VALIDATION_REPORT.md).
It uses actual YOLO + ByteTrack on the available real videos, labels low-light
suitability, and makes no RTSP hardware or production scalability claim.

Phase 12 reliability validation uses deterministic local/synthetic sources and
the existing PostgreSQL database. See
[PHASE12_COMPLETION_REPORT.md](PHASE12_COMPLETION_REPORT.md) for measured
results and limitations.
