# SIH Final Demo Script

## Opening

"NETRAKON AI is running locally with PostgreSQL, FastAPI, YOLO, ByteTrack, behavior and risk services, and a React command center. This demonstration uses two supplied night videos and clearly labels deterministic test events."

## Run of show

1. Start PostgreSQL.
2. Start the backend with `uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000`.
3. Start the frontend with `npm run dev -- --host 127.0.0.1 --port 5173`.
4. Open Command Center at `/dashboard` and show backend and alert WebSocket connected.
5. Start CAM-01 (`YOUR_NIGHT_VIDEO.mp4`) and CAM-02 (`night_test.mp4`).
6. Show the actual feeds and their real resolution/FPS.
7. Point out YOLO boxes, classes, confidence, and ByteTrack IDs.
8. Point out behavior type and score when observations are available.
9. Trigger the existing `/api/ai/intrusion-test` crossing. Say: "This is a deterministic DEMO/TEST event for proving the security flow; it is not fabricated production telemetry."
10. Show event ID, alert ID, camera, boundary, track, direction, severity, timestamp, and PostgreSQL REST history.
11. Show risk score 90, CRITICAL level, and factor explanations in Alert Center.
12. Show the alert arriving over WebSocket without refreshing the page, with no duplicate alert.
13. Show Analytics, Tracking, Sector Map, Camera Management, and Settings.
14. Stop/restart a camera and show truthful STOPPED state after finite-video EOF.

## Closing limitations

Physical RTSP hardware was not validated. No deployment or production scalability claim is made. No ground-truth accuracy benchmark was performed. Individual detection records are not persisted as PostgreSQL rows, and session detection summaries reset after backend restart.

## Optional Live Mobile Camera Run

1. Put the phone and laptop on the same Wi-Fi network.
2. Start any IP camera streaming app on the phone and copy its HTTP/MJPEG URL.
3. In `/cameras`, choose `IP CAMERA / MJPEG`, enter the URL, save, and start the camera.
4. Verify backend `LIVE`, processed video, YOLO detections, ByteTrack IDs, FPS, and current tracks.
5. Demonstrate temporary disconnect behavior as `RECONNECTING`, followed by `LIVE` after the phone stream returns.

Do not claim physical mobile-camera validation unless a reachable phone stream was actually connected during the demo.
