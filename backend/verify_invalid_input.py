"""Verify error handling on invalid video input for POST /api/ai/track."""
import json
import urllib.request
import urllib.error

boundary = "----InvalidBoundary7MA4YWxkTrZu0gW"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="corrupt.txt"\r\n'
    f"Content-Type: text/plain\r\n"
    f"\r\n"
    f"This is not a valid video file format!\r\n"
    f"--{boundary}--\r\n"
).encode()

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/ai/track?conf=0.25&max_frames=10",
    data=body,
    method="POST",
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("[FAIL] Expected error but got HTTP status:", resp.status)
except urllib.error.HTTPError as e:
    print(f"[OK] Graceful error response on invalid input -> HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"[ERR] {e}")
