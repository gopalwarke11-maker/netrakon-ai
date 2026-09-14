"""Verify Phase 3 POST /api/ai/detect endpoint."""
import json
import urllib.request
import numpy as np
import cv2

# Create a sample synthetic test image with a circle or square
img = np.zeros((300, 300, 3), dtype=np.uint8)
cv2.rectangle(img, (50, 50), (200, 200), (0, 255, 0), -1)
_, img_bytes = cv2.imencode(".jpg", img)

boundary = "----ImageBoundary7MA4YWxkTrZu0gW"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="test.jpg"\r\n'
    f"Content-Type: image/jpeg\r\n"
    f"\r\n"
).encode() + img_bytes.tobytes() + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/ai/detect?conf=0.25",
    data=body,
    method="POST",
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode())
        print("[OK] POST /api/ai/detect status:", resp.status)
        print("Response:", json.dumps(res, indent=2))
except urllib.error.HTTPError as e:
    print(f"[ERR] HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"[ERR] {e}")
