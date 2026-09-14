"""Quick API health-check script for Phase 3+4 verification."""
import json
import sys
import urllib.request


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.status, json.loads(r.read())
    except Exception as e:
        return 0, str(e)


checks = [
    ("GET /api/health",     "http://127.0.0.1:8000/api/health"),
    ("GET /api/cameras",    "http://127.0.0.1:8000/api/cameras"),
    ("GET /api/alerts",     "http://127.0.0.1:8000/api/alerts"),
    ("GET /api/detections", "http://127.0.0.1:8000/api/detections"),
]

all_ok = True
for label, url in checks:
    code, body = get(url)
    ok = code == 200
    if not ok:
        all_ok = False
    status = "OK  " if ok else "FAIL"
    print(f"  [{status}]  {label}  ->  HTTP {code}")

print()
if all_ok:
    print("All existing endpoints: PASS")
else:
    print("Some endpoints FAILED - check backend is running")
    sys.exit(1)
