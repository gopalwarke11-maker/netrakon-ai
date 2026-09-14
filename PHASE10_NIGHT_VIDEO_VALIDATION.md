# Phase 10 Night Video Validation

## Video Information

## Sampling

## Low-Light Results

## Detection Comparison

| Metric                   | Original | Enhanced |
| ------------------------ | -------: | -------: |
| total detections         |       81 |      101 |
| average detections/frame |     1.98 |     2.46 |
| average confidence       |   0.5863 |     0.61 |
| person detections        |        1 |        3 |
| vehicle detections       |       32 |       50 |
| other classes            |       48 |       48 |

## Performance

## Tracking Comparison

| Metric                   | Original | Enhanced |
| ------------------------ | -------: | -------: |
| Unique tracks            |       23 |       22 |
| Multi-frame tracks       |       15 |       15 |
| Multi-frame track ratio  |   0.6522 |   0.6818 |
| Average track duration   |     4.39 |      4.5 |
| Maximum track duration   |       40 |       40 |
| Total track observations |      101 |       99 |

These measurements reflect the current development machine and the specific validation sample only.

## Interpretation

This validation is limited to the supplied sample and does not establish model accuracy on all night footage.
Detection count changed by 20 detections across the sampled frames.
Average confidence changed from 0.5863 to 0.61.
Tracking changed from 23 unique tracks to 22 unique tracks with ByteTrack.
The present result is recorded as: ByteTrack continuity was measured across consecutive frames in both streams; the enhancement path is compared against the original path using the same tracker configuration.

## Limitations

## Final Verdict

B. ByteTrack analysis was completed on the real night-video sample and the comparison reflects the measured original-vs-enhanced tracking continuity.

## 1. Automated Software Tests

- Backend regression suite: 73 passed, 1 warning.
- Frontend production build: passed (`tsc -b && vite build`).
- Database migration check: passed; `20260912_03 (head)`.

These checks validate software behavior and project integrity. They do not establish computer-vision accuracy.

## 2. Real-World Night-Video Validation

- input: `backend/validation_input/YOUR_NIGHT_VIDEO.mp4`
- resolution: 1280x720
- FPS: 23.98
- frame count: 408
- duration: 17.02 seconds
- sampling interval: 1
- sampled frames: 408
- low-light frames: 408/408
- low-light percentage: 100.0%
- average luminance: 33.84

The complete video was processed. No frames were skipped by the validator.

## 3. Detection Observations

| Metric               | Original | Enhanced |
| -------------------- | -------: | -------: |
| Total detections     |      994 |     1043 |
| Detections per frame |     2.44 |     2.56 |
| Average confidence   |   0.5758 |   0.5944 |
| Person detections    |       23 |       31 |
| Vehicle detections   |      479 |      528 |
| Other detections     |      492 |      484 |

- Detection delta: +49 detections.
- Relative detection change: +4.93% compared with the original path.
- Relative confidence change: +3.23% compared with the original path.

Detection count increased by 4.93% on this validation sample. This is an observation about model outputs, not a claim that detection accuracy improved; no ground-truth annotations are available.

## 4. Tracking Observations

Both streams used independent `TrackSession` instances with the existing ByteTrack configuration and processed consecutive frames.

| Metric                   | Original | Enhanced |
| ------------------------ | -------: | -------: |
| Unique tracks            |       49 |       52 |
| Multi-frame tracks       |       42 |       45 |
| Multi-frame track ratio  |   0.8571 |   0.8654 |
| Average track duration   |     21.2 |     20.1 |
| Maximum track duration   |      403 |      403 |
| Total track observations |     1039 |     1045 |

- Original continuity: 78 continuity breaks across 49 track IDs.
- Enhanced continuity: measured across the independent enhanced stream; the enhanced stream produced 45 multi-frame tracks and a 0.8654 multi-frame ratio.
- Unique tracks increased by 6.12%, while average track duration decreased by 5.19%.

The full-video tracking result is mixed: enhancement produced more track IDs and multi-frame tracks, but the average duration was lower. This does not establish tracking accuracy without annotations.

## 5. Performance Measurements

- Original average processing time: 31.37 ms/frame
- Enhanced average processing time: 32.16 ms/frame
- Enhancement overhead: +0.79 ms/frame
- Estimated enhanced-path FPS: 31.09

These timings reflect the current development machine and this sample only.

## 6. Full-Run Comparison

The previous 300-frame run reported 715 original detections and 763 enhanced detections, a +6.71% change, with 37 and 40 unique tracks respectively. The complete 408-frame run reports 994 and 1043 detections, a +4.93% change, with 49 and 52 unique tracks.

The full-video result is **consistent** with the previous run in direction: enhancement increased detection counts and unique tracks, and the final verdict remains B. The magnitude is lower for detection change on the complete video, so the full run is the authoritative result.

## Limitations

- One video is not enough to establish model accuracy.
- No ground-truth annotations are available.
- Detection count is not detection accuracy.
- Tracking continuity metrics are not identity accuracy.
- Performance depends on hardware.
- Camera quality, compression, and IR/night-vision characteristics can change results.
- Real CCTV conditions can vary.

## Final Verdict

**B. Enhancement changes detections but benefit is inconclusive on this sample.**

The enhanced path increased detections by 4.93%, increased the multi-frame track ratio from 0.8571 to 0.8654, and increased average confidence by 3.23%. However, it also reduced average track duration from 21.2 to 20.1 frames, and there is no ground truth to determine whether additional detections or tracks are correct.
