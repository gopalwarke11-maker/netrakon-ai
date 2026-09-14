# NETRAKON AI System Architecture

## Runtime topology

```text
React + TypeScript + Vite
        | REST /api and WS /ws/alerts
        v
FastAPI application
        |
        +-- health/readiness
        +-- camera CRUD and lifecycle manager
        +-- YOLO detection
        +-- ByteTrack tracking and track history
        +-- low-light / CLAHE preprocessing
        +-- virtual boundaries and intrusion state
        +-- behavior analysis
        +-- risk assessment
        +-- alert WebSocket fan-out
        v
PostgreSQL via SQLAlchemy + Alembic
```

## Source-of-truth boundaries

PostgreSQL is the source of truth for cameras, boundaries, alerts, intrusion events, and behavior observations. Runtime worker state, frame-level detections, and track histories are process state and are not a replacement for persisted domain history.

Each camera is keyed by `camera_id`. Its worker owns the source, tracking session, history, and lifecycle state. Numeric track IDs may repeat across cameras; database queries and behavior identity remain camera-scoped.

## AI flow

```text
video/image -> low-light classification and optional CLAHE -> YOLO -> ByteTrack
-> track history -> virtual boundary evaluation -> intrusion event
-> behavior and risk services -> PostgreSQL -> WebSocket -> frontend
```

The uploaded-image and uploaded-video AI endpoints are development/testing interfaces. Local file processing is validated. Physical RTSP and browser-runtime E2E are **NOT VALIDATED**.

## API contracts

- Health: `GET /api/health`, `GET /api/ready`
- Cameras: `/api/cameras` plus `/api/cameras/{id}/start`, `/stop`, `/restart`, `/status`, and `/api/cameras/runtime`
- Domain data: `/api/alerts`, `/api/detections`, `/api/boundaries`, `/api/intrusions`
- AI: `/api/ai/detect`, `/track`, `/intrusion-test`, `/risk-test`, `/behavior-test`, `/low-light-test`
- Events: `WS /ws/alerts`

## Operational guarantees and limits

**VALIDATED**: database startup check, Alembic head, camera CRUD/lifecycle, deterministic persistence/restart tests, full regression, low-light processing, local real-video artifacts, and WebSocket delivery.

**KNOWN LIMITATION**: the current service is a local SIH demonstration system. No production scalability, hardware RTSP, authentication/authorization, or browser automation claim is made.
