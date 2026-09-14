#!/usr/bin/env python
"""Check frontend build status."""
import subprocess
import sys

print("=== Frontend Verification ===\n")

# Check if npm is installed
try:
    result = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=10)
    print(f"✓ npm version: {result.stdout.strip()}")
except Exception as e:
    print(f"✗ npm not found: {e}")
    sys.exit(1)

# Check if TypeScript is installed
try:
    result = subprocess.run(["npm", "list", "typescript"], cwd="d:\\sih\\netrakon-ai\\frontend", capture_output=True, text=True, timeout=10)
    if "typescript" in result.stdout:
        print(f"✓ TypeScript is installed")
    else:
        print(f"✗ TypeScript not found in package.json")
except Exception as e:
    print(f"✗ Error checking TypeScript: {e}")

# Check if dist folder exists
import os
dist_path = "d:\\sih\\netrakon-ai\\frontend\\dist"
if os.path.exists(dist_path):
    print(f"✓ dist/ folder exists (size: {len(os.listdir(dist_path))} items)")
else:
    print(f"ℹ dist/ folder does not exist (needs build)")

# Check package.json
try:
    import json
    with open("d:\\sih\\netrakon-ai\\frontend\\package.json") as f:
        pkg = json.load(f)
    print(f"\n✓ Package name: {pkg.get('name')}")
    print(f"✓ Version: {pkg.get('version')}")
    if "build" in pkg.get("scripts", {}):
        print(f"✓ Build script: {pkg['scripts']['build']}")
except Exception as e:
    print(f"✗ Error reading package.json: {e}")

print("\n✓ Frontend verification complete")
