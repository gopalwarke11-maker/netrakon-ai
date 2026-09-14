# Phase 13 Real-World Multi-Camera Validation

## Final Status

**PARTIAL**

Two distinct real local video files were processed with actual YOLO and ByteTrack. CAM-01 is highly suitable night footage; CAM-02 is a distinct real security video but is not night-suitable under the existing low-light threshold. The multi-camera concurrent run passed. Phase 13 remains partial because no physical RTSP hardware or browser-runtime E2E was available, and no production scalability claim is made.

## Objective and Scope

Validate the existing NETRAKON pipeline against real local videos while preserving camera-scoped tracking, intrusion, risk, behavior, persistence, and WebSocket ownership.

The primary identity scope is `(camera_id, track_id)`. Numeric track IDs may repeat between cameras.

## Videos Tested

| Camera | File                                    | Resolution |    FPS | Duration | Frames |            Size | Suitability                       |
| ------ | --------------------------------------- | ---------: | -----: | -------: | -----: | --------------: | --------------------------------- |
| CAM-01 | `validation_input/YOUR_NIGHT_VIDEO.mp4` |   1280x720 | 23.976 |  17.017s |    408 | 6,006,209 bytes | HIGHLY SUITABLE                   |
| CAM-02 | `validation_input/night_test.mp4`       |   1280x720 |   25.0 |   57.96s |   1449 | 5,952,051 bytes | NOT SUITABLE for night validation |

`backend/_test_synth.mp4` was identified as a project synthetic fixture and was not represented as a real camera source.

## Configuration

- YOLO model: `yolov8n.pt`
- Tracker: `bytetrack.yaml`
- Tracking confidence: `0.25`
- Low-light enabled: `true`
- Low-light threshold: `70.0`
- CAM-01 enhancement: enabled
- CAM-02 enhancement: disabled because only 2.83% of frames were low-light

## CAM-01 Real Night Validation

- Low-light: 408/408 frames, 100.0%
- Average luminance: 33.844
- Detections: 981, 2.404/frame
- Average confidence: 0.6015
- Classes: car 474, truck 5, traffic light 474, person 24, parking meter 4
- Unique tracks: 29
- Multi-frame tracks: 26
- Multi-frame ratio: 0.8966
- Average track duration: 33.828 frames
- Maximum track duration: 405 frames
- Track observations: 981
- Processing: 24.014 seconds, 56.577 ms/frame, 17.675 FPS
- Behaviors: 25 observations
- Behavior types: RAPID_MOVEMENT 14, ABNORMAL_MOVEMENT 8, DIRECTION_REVERSAL 3

### Intrusion and Risk

The existing CAM-01 database configuration contained multiple enabled boundaries. The validator did not invent or alter geometry. The real run produced six actual crossings against configured boundaries:

- Intrusions: 6
- Severity: HIGH 6
- Direction: UNRESTRICTED_TO_RESTRICTED 6
- Risk assessments: 6
- Risk level: HIGH 6
- Risk scores observed: 65 and 70
- Risk fields and factors were persisted in PostgreSQL

The detected object for these events was `traffic light`; this is an observed model output, not a claim that the object is a security subject.

## CAM-02 Real Video Validation

- Low-light: 41/1449 frames, 2.83%
- Average luminance: 95.3
- Night suitability: NOT SUITABLE
- Detections: 5382, 3.714/frame
- Average confidence: 0.7821
- Classes: car 4273, person 1068, kite 41
- Unique tracks: 19
- Multi-frame tracks: 17
- Multi-frame ratio: 0.8947
- Average track duration: 283.263 frames
- Maximum track duration: 1259 frames
- Track observations: 5382
- Intrusions: 0, scenario not observed
- Risk: NOT EXERCISED because no intrusion was generated
- Behaviors: 44 observations
- Behavior types: RAPID_MOVEMENT 7, DIRECTION_REVERSAL 14, ABNORMAL_MOVEMENT 16, STATIONARY 3, LOITERING 4
- Processing: 53.717 seconds, 35.177 ms/frame, 28.427 FPS
- Errors: none

## Concurrent Real Multi-Camera Validation

Actual `CameraManager` workers processed both real local videos concurrently for 60 frames per camera:

| Camera | Frames | Detections | Active tracks | Worker FPS | Status  | Errors |
| ------ | -----: | ---------: | ------------: | ---------: | ------- | ------ |
| CAM-01 |     60 |        150 |            10 |       8.55 | STOPPED | none   |
| CAM-02 |     60 |         27 |             3 |      10.57 | STOPPED | none   |

- Total wall time: 8.989 seconds
- Combined measured FPS: 13.349
- Actual YOLO + ByteTrack: yes
- Camera identity scope: `(camera_id, track_id)`
- RTSP hardware: not tested
- Production scalability: not claimed

## PostgreSQL and WebSocket

Real processing wrote camera-scoped behavior observations and, for CAM-01, intrusion events, alerts, and risk fields through the existing services. WebSocket publication used the existing production path and preserved camera, boundary, track, severity, direction, risk, and behavior fields. REST/database records remain authoritative.

Validation-created records were identified for cleanup after measurement; no pre-existing user records, tables, or camera/boundary configuration were reset or deleted.

## Failure Isolation

The existing Phase 12 manager failure-isolation tests remain passing. A real concurrent invalid-source run was not added to this report as a separate YOLO benchmark; no failure is claimed beyond the tested manager contract.

## Tests and Regression

- Phase 13 focused tests: 4 passed / 0 failed
- Full backend regression: 131 passed / 0 failed
- Frontend build: PASS
- Frontend lint: PASS
- Alembic current: `20260912_03 (head)`
- Alembic heads: `20260912_03 (head)`

## Limitations

- No physical RTSP stream or camera device was tested.
- CAM-02 is real CCTV/security footage but not night-suitable.
- No browser-runtime E2E was performed.
- No ground-truth annotations are available; observed detections, tracks, and behaviors are not accuracy measurements.
- Local CPU performance is hardware-specific and is not a production throughput claim.
- Existing configured CAM-01 boundaries included test-named boundaries; the validator reported their actual events and did not claim a new field scenario.

## Verdict

**PARTIAL: real local multi-camera validation succeeded, but RTSP hardware and browser-runtime validation were not performed, and the second available real video was not night-suitable.**
