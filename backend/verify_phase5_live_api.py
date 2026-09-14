"""Live HTTP verification for Phase 5 Virtual Boundary and Intrusion APIs."""

import json
import urllib.request
import urllib.error
import sys

BASE = "http://127.0.0.1:8000/api"


def request(method: str, path: str, data: dict | None = None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
            parsed = json.loads(raw) if raw else None
            return status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        parsed = json.loads(raw) if raw else None
        return e.code, parsed
    except Exception as e:
        return 0, str(e)


def run_checks():
    print("=== NETRAKON AI Phase 5 Live API Verification ===")

    # 1. GET /api/boundaries
    code, res = request("GET", "/boundaries")
    assert code == 200, f"GET /boundaries failed: {code}"
    print(f"[OK] GET /api/boundaries -> {code}, found {len(res)} boundaries")

    # 2. POST /api/boundaries
    new_bnd = {
        "camera_id": "CAM-01",
        "name": "Live Test Boundary",
        "enabled": True,
        "point_a": {"x": 50.0, "y": 200.0},
        "point_b": {"x": 750.0, "y": 200.0},
        "restricted_side": "positive",
        "severity": "HIGH",
        "tolerance": 5.0,
    }
    code, created = request("POST", "/boundaries", new_bnd)
    assert code == 201, f"POST /boundaries failed: {code}, {created}"
    bnd_id = created["id"]
    print(f"[OK] POST /api/boundaries -> {code}, created boundary {bnd_id}")

    # 3. GET /api/boundaries/{boundary_id}
    code, fetched = request("GET", f"/boundaries/{bnd_id}")
    assert code == 200 and fetched["id"] == bnd_id
    print(f"[OK] GET /api/boundaries/{bnd_id} -> {code}")

    # 4. PUT /api/boundaries/{boundary_id}
    code, updated = request("PUT", f"/boundaries/{bnd_id}", {"name": "Live Test Boundary Renamed"})
    assert code == 200 and updated["name"] == "Live Test Boundary Renamed"
    print(f"[OK] PUT /api/boundaries/{bnd_id} -> {code}, updated name")

    # 5. GET /api/cameras/CAM-01/boundaries
    code, cam_bnds = request("GET", "/cameras/CAM-01/boundaries")
    assert code == 200 and any(b["id"] == bnd_id for b in cam_bnds)
    print(f"[OK] GET /api/cameras/CAM-01/boundaries -> {code}, contains {bnd_id}")

    # 6. Validation: Identical points A and B
    invalid_pts = dict(new_bnd, point_b={"x": 50.0, "y": 200.0})
    code, _ = request("POST", "/boundaries", invalid_pts)
    assert code == 422, f"Expected 422 for identical points, got {code}"
    print(f"[OK] POST /api/boundaries (identical A/B) -> {code} validation error")

    # 7. Validation: Nonexistent camera
    invalid_cam = dict(new_bnd, camera_id="CAM-GHOST")
    code, _ = request("POST", "/boundaries", invalid_cam)
    assert code == 400, f"Expected 400 for nonexistent camera, got {code}"
    print(f"[OK] POST /api/boundaries (invalid camera) -> {code} bad request error")

    # 8. POST /api/ai/intrusion-test
    sim_req = {
        "camera_id": "CAM-01",
        "custom_boundary": {
            "name": "Live Simulation Line",
            "camera_id": "CAM-01",
            "enabled": True,
            "point_a": {"x": 100.0, "y": 300.0},
            "point_b": {"x": 800.0, "y": 300.0},
            "restricted_side": "positive",
            "severity": "HIGH",
            "tolerance": 5.0,
        },
        "frames": [
            {"frame_number": 1, "tracks": [{"track_id": 99, "class_name": "person", "anchor_x": 450.0, "anchor_y": 200.0}]},
            {"frame_number": 2, "tracks": [{"track_id": 99, "class_name": "person", "anchor_x": 450.0, "anchor_y": 250.0}]},
            {"frame_number": 3, "tracks": [{"track_id": 99, "class_name": "person", "anchor_x": 450.0, "anchor_y": 380.0}]},  # Crossing
            {"frame_number": 4, "tracks": [{"track_id": 99, "class_name": "person", "anchor_x": 450.0, "anchor_y": 420.0}]},  # Stays inside
        ],
    }
    code, sim_res = request("POST", "/ai/intrusion-test", sim_req)
    assert code == 200, f"POST /ai/intrusion-test failed: {code}, {sim_res}"
    assert sim_res["is_simulation"] is True
    assert sim_res["intrusions_detected"] == 1
    assert len(sim_res["events"]) == 1
    assert len(sim_res["alerts_generated"]) == 1
    print(f"[OK] POST /api/ai/intrusion-test -> {code}, 1 intrusion detected, alert generated: {sim_res['alerts_generated'][0]['id']}")

    # 9. DELETE /api/boundaries/{boundary_id}
    code, _ = request("DELETE", f"/boundaries/{bnd_id}")
    assert code == 204
    print(f"[OK] DELETE /api/boundaries/{bnd_id} -> {code}")

    # 10. Confirm 404 after delete
    code, _ = request("GET", f"/boundaries/{bnd_id}")
    assert code == 404
    print(f"[OK] GET /api/boundaries/{bnd_id} after delete -> {code} Not Found")

    print("\nALL PHASE 5 LIVE API CHECKS PASSED SUCCESSFULLY!\n")


if __name__ == "__main__":
    run_checks()
