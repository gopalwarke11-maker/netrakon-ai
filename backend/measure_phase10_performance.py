#!/usr/bin/env python
"""Performance measurement for Phase 10 low-light enhancement."""

import time

import cv2
import numpy as np

from app.ai.low_light import get_processor


def measure_enhancement_overhead():
    """Measure the processing time for low-light enhancement."""
    processor = get_processor()
    
    # Create a series of frames
    frame_sizes = [(480, 640), (720, 1280), (1080, 1920)]
    enhancement_times = {}
    
    print("=== Low-Light Enhancement Performance ===\n")
    
    for height, width in frame_sizes:
        # Test bright frame (no enhancement)
        frame_bright = np.full((height, width, 3), 200, dtype=np.uint8)
        
        t0 = time.perf_counter()
        for _ in range(10):
            processor.process_frame(frame_bright, enable_enhancement=True)
        time_bright = (time.perf_counter() - t0) / 10  # avg time
        
        # Test dark frame (with enhancement)
        frame_dark = np.full((height, width, 3), 30, dtype=np.uint8)
        
        t0 = time.perf_counter()
        for _ in range(10):
            processor.process_frame(frame_dark, enable_enhancement=True)
        time_dark = (time.perf_counter() - t0) / 10  # avg time
        
        enhancement_times[f"{width}x{height}"] = {
            "bright_frame_ms": time_bright * 1000,
            "dark_frame_with_enhancement_ms": time_dark * 1000,
            "enhancement_overhead_ms": (time_dark - time_bright) * 1000,
        }
    
    for size, times in enhancement_times.items():
        print(f"Frame Size: {size}")
        print(f"  Bright frame (no enhancement):     {times['bright_frame_ms']:.3f} ms")
        print(f"  Dark frame (with CLAHE):           {times['dark_frame_with_enhancement_ms']:.3f} ms")
        print(f"  Enhancement overhead:             {times['enhancement_overhead_ms']:.3f} ms")
        print()


def measure_clahe_only():
    """Measure CLAHE processing time independently."""
    print("=== CLAHE Processing Time (Independent) ===\n")
    
    processor = get_processor()
    
    frame_sizes = [(480, 640), (720, 1280), (1080, 1920)]
    
    for height, width in frame_sizes:
        frame = np.full((height, width, 3), 50, dtype=np.uint8)
        
        t0 = time.perf_counter()
        for _ in range(10):
            processor.enhance_clahe(frame)
        avg_time = (time.perf_counter() - t0) / 10
        
        pixels = height * width
        fps_equivalent = 1.0 / avg_time if avg_time > 0 else 0
        
        print(f"Frame Size: {width}x{height} ({pixels:,} pixels)")
        print(f"  CLAHE time per frame:    {avg_time * 1000:.3f} ms")
        print(f"  Equivalent FPS capacity: {fps_equivalent:.1f} frames/sec")
        print()


if __name__ == "__main__":
    measure_enhancement_overhead()
    measure_clahe_only()
    print("✓ Performance measurement complete")
