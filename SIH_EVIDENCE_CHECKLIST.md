# SIH Final Evidence Checklist

| Area                              | Status        | Evidence                                                                              |
| --------------------------------- | ------------- | ------------------------------------------------------------------------------------- |
| CAM-01                            | VALIDATED     | `YOUR_NIGHT_VIDEO.mp4`; 1280x720, 23.976 FPS source, real boxes/classes, IDs, history |
| CAM-02                            | VALIDATED     | `night_test.mp4`; 1280x720, 25 FPS source, real boxes/classes, IDs, history           |
| YOLO and boxes                    | VALIDATED     | Live current detections included traffic light/car/person/car boxes                   |
| ByteTrack                         | VALIDATED     | Track IDs and historical tracks retained after EOF                                    |
| Behavior                          | VALIDATED     | Backend behavior observations and deterministic behavior-test mechanism               |
| Intrusion flow                    | VALIDATED     | DEMO/TEST `EVT-0007`, CAM-01, `DEMO-BND-01`, track 9001                               |
| Risk                              | VALIDATED     | REST score 90, CRITICAL, five factor explanations                                     |
| Alert                             | VALIDATED     | `ALT-0007`, HIGH, persisted and shown in Alert Center                                 |
| PostgreSQL                        | VALIDATED     | Event, alert, boundary, risk, and alert history REST reads succeeded                  |
| WebSocket                         | VALIDATED     | Alert Stream Connected; dashboard updated without refresh                             |
| Analytics                         | VALIDATED     | 5466 detections, 28 historical tracks, 7 intrusions, 7 alerts, 78% confidence         |
| Tracking                          | VALIDATED     | Active tracks separated from historical tracks; EOF active tracks 0                   |
| Sector map                        | VALIDATED     | CONCEPTUAL MAP, CAM-01/CAM-02, sectors and risk shown                                 |
| Camera management                 | VALIDATED     | Start, status, stop, restart, refresh; EOF is STOPPED                                 |
| Browser pages                     | VALIDATED     | Dashboard, `/live-cameras`, alerts, tracking, analytics, sectors, cameras, settings   |
| Backend regression                | VALIDATED     | 131 passed, 1 warning                                                                 |
| Frontend build                    | VALIDATED     | `npm run build` passed                                                                |
| Frontend lint                     | VALIDATED     | `npm run lint` passed                                                                 |
| Physical RTSP                     | NOT VALIDATED | No physical RTSP hardware was available                                               |
| Production deployment/scalability | NOT VALIDATED | Local demonstration only                                                              |
| Detection accuracy benchmark      | NOT VALIDATED | No ground-truth benchmark performed                                                   |
| Detection-row persistence         | LIMITATION    | Individual detection records are not PostgreSQL rows                                  |
| Restart behavior                  | LIMITATION    | Session detection summaries reset after backend restart                               |
| Deployment/GitHub                 | NOT PERFORMED | No deployment and no push performed                                                   |
