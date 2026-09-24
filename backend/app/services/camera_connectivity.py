"""Camera connectivity validation service.

Tests stream reachability, handles private LAN detection, and distinguishes
between invalid URLs, private network addresses, unreachable targets, and reachable cameras.
"""

import ipaddress
import logging
from pathlib import Path
import socket
from typing import Any
import urllib.error
import urllib.request
from urllib.parse import urlparse

import cv2

from app.models.camera import CameraTestResponse

logger = logging.getLogger(__name__)


def is_private_ip(ip_str: str) -> bool:
    """Return True if ip_str represents a private, loopback, or link-local IP address."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return False


def check_private_network(hostname: str) -> tuple[bool, str]:
    """Check whether a hostname or IP address belongs to a private network.

    Returns: (is_private, resolved_ip_or_hostname)
    """
    clean_host = hostname.strip().lower()
    if clean_host in {"localhost", "127.0.0.1", "::1"} or clean_host.endswith((".local", ".internal", ".lan")):
        return True, clean_host

    if is_private_ip(clean_host):
        return True, clean_host

    try:
        resolved_ip = socket.gethostbyname(clean_host)
        if is_private_ip(resolved_ip):
            return True, resolved_ip
        return False, resolved_ip
    except socket.gaierror:
        return False, clean_host


def test_camera_stream_connectivity(source_type: str, stream_url: str) -> CameraTestResponse:
    """Test camera stream connectivity and return detailed reachability analysis."""
    url_clean = stream_url.strip()

    # 1. Handle DEVICE source
    if source_type == "DEVICE":
        try:
            device_idx = int(url_clean)
            cap = cv2.VideoCapture(device_idx)
            opened = cap.isOpened()
            cap.release()
            if opened:
                return CameraTestResponse(
                    is_reachable=True,
                    status="DEVICE_AVAILABLE",
                    message=f"Local camera device index {device_idx} is open and available.",
                    details={"device_index": device_idx},
                )
            return CameraTestResponse(
                is_reachable=False,
                status="DEVICE_UNAVAILABLE",
                message=f"Local camera device index {device_idx} could not be opened.",
                details={"device_index": device_idx},
            )
        except ValueError:
            return CameraTestResponse(
                is_reachable=False,
                status="INVALID_URL",
                message="DEVICE camera source must be an integer device index (e.g., '0', '1').",
            )

    # 2. Handle Local FILE source
    if source_type == "FILE" and not url_clean.lower().startswith(("http://", "https://")):
        file_path = Path(url_clean)
        if file_path.is_file():
            return CameraTestResponse(
                is_reachable=True,
                status="REACHABLE",
                message=f"Local video file found at '{file_path.name}'.",
                details={"path": str(file_path), "size_bytes": file_path.stat().st_size},
            )
        return CameraTestResponse(
            is_reachable=False,
            status="UNREACHABLE",
            message=f"Local video file not found at path '{url_clean}'.",
            details={"path": url_clean},
        )

    # 3. Handle Network Streams (RTSP, MJPEG, Remote FILE)
    parsed = urlparse(url_clean)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname

    # Format validation for RTSP and MJPEG
    if source_type == "RTSP" and scheme not in {"rtsp", "rtsps"}:
        return CameraTestResponse(
            is_reachable=False,
            status="INVALID_URL",
            message="RTSP cameras require an 'rtsp://' or 'rtsps://' scheme.",
            details={"provided_scheme": scheme},
        )
    if source_type == "MJPEG" and scheme not in {"http", "https"}:
        return CameraTestResponse(
            is_reachable=False,
            status="INVALID_URL",
            message="MJPEG cameras require an 'http://' or 'https://' scheme.",
            details={"provided_scheme": scheme},
        )
    if source_type == "FILE" and scheme not in {"http", "https"}:
        return CameraTestResponse(
            is_reachable=False,
            status="INVALID_URL",
            message="Remote FILE cameras require an 'http://' or 'https://' scheme.",
            details={"provided_scheme": scheme},
        )

    if not hostname:
        return CameraTestResponse(
            is_reachable=False,
            status="INVALID_URL",
            message="Camera stream URL is missing a valid host name or IP address.",
        )

    # 4. Private LAN Detection
    is_private, resolved_ip = check_private_network(hostname)
    if is_private:
        return CameraTestResponse(
            is_reachable=False,
            status="PRIVATE_NETWORK_NOT_REACHABLE",
            message=(
                f"Private network address ({hostname}) is not directly reachable from cloud production server. "
                "Please expose it via a secure tunnel (e.g. Cloudflare Tunnel or Tailscale) or use a public camera endpoint."
            ),
            details={
                "hostname": hostname,
                "ip": resolved_ip,
                "scheme": scheme,
                "port": parsed.port,
                "note": "Production Render server cannot cross private LAN boundaries without a secure public tunnel.",
            },
        )

    # 5. Public RTSP Socket Reachability Check
    if scheme in {"rtsp", "rtsps"}:
        port = parsed.port or (322 if scheme == "rtsps" else 554)
        try:
            with socket.create_connection((hostname, port), timeout=5.0):
                return CameraTestResponse(
                    is_reachable=True,
                    status="REACHABLE",
                    message=f"RTSP stream port {port} on '{hostname}' is open and reachable.",
                    details={"hostname": hostname, "port": port},
                )
        except socket.timeout:
            return CameraTestResponse(
                is_reachable=False,
                status="UNREACHABLE",
                message=f"Connection timed out when reaching RTSP server '{hostname}:{port}' (5.0s limit).",
                details={"hostname": hostname, "port": port},
            )
        except ConnectionRefusedError:
            return CameraTestResponse(
                is_reachable=False,
                status="UNREACHABLE",
                message=f"Connection refused by RTSP server at '{hostname}:{port}'.",
                details={"hostname": hostname, "port": port},
            )
        except Exception as exc:
            return CameraTestResponse(
                is_reachable=False,
                status="UNREACHABLE",
                message=f"Failed to reach RTSP endpoint: {exc}",
                details={"hostname": hostname, "port": port, "error": str(exc)},
            )

    # 6. Public HTTP/HTTPS Reachability Check (MJPEG or Remote FILE)
    try:
        req = urllib.request.Request(
            url_clean,
            headers={"User-Agent": "NetraKon-AI/1.0"},
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            status_code = getattr(resp, "status", 200)
            return CameraTestResponse(
                is_reachable=True,
                status="REACHABLE",
                message=f"HTTP camera stream responded with status {status_code}.",
                details={"http_status": status_code, "hostname": hostname},
            )
    except urllib.error.HTTPError as exc:
        # HTTP 401 Unauthorized or 403 Forbidden means endpoint IS reachable over network but needs auth
        if exc.code in {401, 403}:
            return CameraTestResponse(
                is_reachable=True,
                status="REACHABLE",
                message=f"Camera endpoint is reachable (HTTP {exc.code} authentication required).",
                details={"http_status": exc.code, "hostname": hostname},
            )
        return CameraTestResponse(
            is_reachable=False,
            status="UNREACHABLE",
            message=f"Camera endpoint returned HTTP error {exc.code}: {exc.reason}",
            details={"http_status": exc.code, "hostname": hostname},
        )
    except urllib.error.URLError as exc:
        reason = str(exc.reason)
        if "timed out" in reason.lower():
            return CameraTestResponse(
                is_reachable=False,
                status="UNREACHABLE",
                message=f"HTTP connection to camera '{hostname}' timed out after 5.0 seconds.",
                details={"hostname": hostname, "reason": reason},
            )
        return CameraTestResponse(
            is_reachable=False,
            status="UNREACHABLE",
            message=f"HTTP request to camera '{hostname}' failed: {reason}",
            details={"hostname": hostname, "reason": reason},
        )
    except Exception as exc:
        return CameraTestResponse(
            is_reachable=False,
            status="UNREACHABLE",
            message=f"Failed to reach HTTP camera endpoint: {exc}",
            details={"hostname": hostname, "error": str(exc)},
        )
