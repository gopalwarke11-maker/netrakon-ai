# Phase 10 Night Video Validation

## Video Information

- filename: YOUR_NIGHT_VIDEO.mp4
- resolution: 1280x720
- FPS: 23.98
- frame count: 408
- duration: 17.02 seconds
- codec: h264

## Sampling

- sampling interval: 1
- number of frames analyzed: 408

## Low-Light Results

- low-light frames: 408
- percentage low-light: 100.0%
- average luminance: 33.84

## Detection Comparison

| Metric | Original | Enhanced |
| --- | ---: | ---: |
| total detections | 994 | 1043 |
| average detections/frame | 2.44 | 2.56 |
| average confidence | 0.5758 | 0.5944 |
| person detections | 23 | 31 |
| vehicle detections | 479 | 528 |
| other classes | 492 | 484 |

## Performance

- original average processing ms: 28.46
- enhanced average processing ms: 29.34
- overhead ms: 0.88
- estimated FPS: 34.08

## Tracking Comparison

| Metric | Original | Enhanced |
| --- | ---: | ---: |
| Unique tracks | 49 | 52 |
| Multi-frame tracks | 42 | 45 |
| Multi-frame track ratio | 0.8571 | 0.8654 |
| Average track duration | 21.2 | 20.1 |
| Maximum track duration | 403 | 403 |
| Total track observations | 1039 | 1045 |

These measurements reflect the current development machine and the specific validation sample only.

## Interpretation

This validation is limited to the supplied sample and does not establish model accuracy on all night footage.
Detection count changed by 49 detections across the sampled frames.
Average confidence changed from 0.5758 to 0.5944.
Tracking changed from 49 unique tracks to 52 unique tracks with ByteTrack.
The present result is recorded as: ByteTrack continuity was measured across consecutive frames in both streams; the enhancement path is compared against the original path using the same tracker configuration.

## Limitations

- One video is not enough to establish model accuracy.
- No ground-truth annotations are available unless explicitly provided.
- Performance depends on hardware.
- Camera quality matters.
- IR/night-vision footage may behave differently.
- Real CCTV conditions can vary.

## Final Verdict

B. ByteTrack analysis was completed on the real night-video sample and the comparison reflects the measured original-vs-enhanced tracking continuity.

