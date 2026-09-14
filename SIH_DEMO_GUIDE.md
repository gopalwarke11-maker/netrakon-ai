# NETRAKON AI SIH Local Demo Guide

## Exact startup sequence

1. Start PostgreSQL and confirm the local `netrakon` database is available.
2. Start the backend:

```powershell
cd D:\sih\netrakon-ai\backend
.\venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000
```

3. Start the frontend:

```powershell
cd D:\sih\netrakon-ai\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

4. Open `http://127.0.0.1:5173/dashboard` (Command Center).

## Demonstration sequence

1. Show `BACKEND CONNECTED`, `ALERT STREAM CONNECTED`, camera inventory, and the conceptual sector map.
2. Open `/cameras` and show CAM-01 and CAM-02 configured as local FILE sources.
3. Start CAM-01 and CAM-02. Use these exact sources:
   - CAM-01: `backend/validation_input/YOUR_NIGHT_VIDEO.mp4`
   - CAM-02: `backend/validation_input/night_test.mp4`
4. Open `/live-cameras` and show actual video, resolution, FPS, YOLO boxes, object classes, confidence, and Track IDs while processing.
5. Show behavior observations when available, including type and score. Behavior-test output is deterministic validation data and must be labeled DEMO/TEST.
6. Trigger `/api/ai/intrusion-test` with the documented geometric crossing payload. Label it `DEMO/TEST`; it is not a live YOLO event.
7. Show the generated event and alert: `EVT-0007`, `ALT-0007`, CAM-01, `DEMO-BND-01`, track 9001, HIGH severity, and `UNRESTRICTED_TO_RESTRICTED` direction.
8. Show the risk assessment from REST and Alert Center: score 90, level CRITICAL, and the five factor explanations.
9. Show the alert arriving through WebSocket without refresh, then open `/alerts` and verify the same alert is in REST history.
10. Show PostgreSQL persistence through the alert and intrusion REST records.
11. Open `/tracking` and distinguish `ACTIVE TRACKS` from historical session tracks. After EOF, active tracks may be 0 while historical tracks remain.
12. Open `/analytics` and show SESSION + LIVE DATA, detections, historical tracks, intrusion events, alerts, classes, cameras, and confidence.
13. Open `/sectors` and show the `CONCEPTUAL MAP`, both configured cameras, sectors, boundaries, and risk state.
14. Open `/cameras` and demonstrate refresh, start, stop, and restart. A finite video must not remain LIVE after EOF.
15. Open `/settings` and show backend-aware local status.

## Validation evidence

- CAM-01 live run: 1280x720, source FPS 23.976, real `traffic light` and `car` boxes, Track IDs, and historical tracks.
- CAM-02 live run: 1280x720, source FPS 25, real `car` and `person` boxes, Track IDs, and historical tracks.
- Final EOF state: CAM-01 STOPPED with 29 historical tracks; CAM-02 STOPPED with 20 historical tracks.
- Backend regression: 131 passed, 1 warning.
- Frontend build and lint: passed.
- Browser route QA: dashboard, `/live-cameras`, `/alerts`, `/tracking`, `/analytics`, `/sectors`, `/cameras`, and `/settings` rendered with backend data.

## Limitations

Physical RTSP hardware, production deployment/scalability, and ground-truth detection accuracy were not validated. Individual detections are not persisted as PostgreSQL rows, and session detection summaries reset after backend restart. The deterministic intrusion, risk, and behavior test endpoints are DEMO/TEST mechanisms, not production camera inference.

## Live Mobile Camera Setup

NETRAKON also accepts a local phone/IP camera stream without internet access.

1. Install any IP camera streaming app on the phone; no specific app is mandatory.
2. Connect the phone and backend laptop to the same Wi-Fi network.
3. Start the camera server on the phone and copy its HTTP/MJPEG URL, for example `http://192.168.1.25:8080/video`.
4. Open `/cameras`, select `IP CAMERA / MJPEG`, enter the URL, and save the camera.
5. Start the camera and wait for `LIVE`; network sources use `RECONNECTING` and then `ERROR` after bounded retries if unavailable.
6. Open `/live-cameras` and verify the processed stream, YOLO boxes, classes, confidence, Track IDs, FPS, and active tracks.
7. Open `/sectors` and verify the camera marker and current track count.

The backend laptop must be able to reach the phone URL on the local network. Credentials are not stored in frontend source or written to logs. The physical phone stream was not available in this validation environment, so mobile configuration is implemented but physical-phone connectivity is not claimed as verified.
