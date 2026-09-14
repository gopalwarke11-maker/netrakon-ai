"""Verify error handling on corrupt mp4 file for POST /api/ai/track."""
import json
import urllib.request
import urllib.error

boundary = "----CorruptBoundary7MA4YWxkTrZu0gW"
corrupt_bytes = b"ftypisom" + b"\x00" * 50

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="corrupt.mp4"\r\n'
    f"Content-Type: video/mp4\r\n"
    f"\r\n"
).encode() + corrupt_bytes + f"\r\n--{boundary}--\r\n".encode()

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
    print(f"[OK] Graceful error response on corrupt MP4 -> HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"[ERR] {e}")
