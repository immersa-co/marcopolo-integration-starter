#!/usr/bin/env bash
set -euo pipefail

missing=0

for cmd in git python3 pip node npm; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd"
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "All required commands are installed."
