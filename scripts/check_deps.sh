#!/usr/bin/env bash
set -euo pipefail

command -v python >/dev/null || { echo "python not found"; exit 1; }
command -v pip >/dev/null || { echo "pip not found"; exit 1; }

if command -v cloudflared >/dev/null; then
  echo "cloudflared: OK"
else
  echo "cloudflared: MISSING (recommended)"
fi

if command -v ngrok >/dev/null; then
  echo "ngrok: OK (fallback)"
else
  echo "ngrok: MISSING (optional)"
fi
