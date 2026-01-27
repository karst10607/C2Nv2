#!/usr/bin/env bash
set -euo pipefail

# Download cloudflared binaries appropriate for the host, place into bundled_tools/
# Used at build time so we don't commit large binaries to git.

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
TOOLS_DIR="$PROJECT_DIR/bundled_tools"
mkdir -p "$TOOLS_DIR"

detect_arch() {
  local arch
  arch=$(uname -m)
  case "$arch" in
    x86_64|amd64) echo amd64 ;;
    arm64|aarch64) echo arm64 ;;
    *) echo "Unsupported arch: $arch" >&2; exit 1 ;;
  esac
}

ARCH=$(detect_arch)
URL_BASE="https://github.com/cloudflare/cloudflared/releases/latest/download"
TARGET="$TOOLS_DIR/cloudflared-$ARCH"

if [ ! -f "$TARGET" ]; then
  echo "Downloading cloudflared for $ARCH ..."
  curl -fsSL -o "$TARGET" "$URL_BASE/cloudflared-darwin-$ARCH.tgz" || true
  if [ -s "$TARGET" ]; then
    echo "Unexpected archive format; removing..." && rm -f "$TARGET"
  fi

  TMP_TGZ="$TOOLS_DIR/cloudflared-$ARCH.tgz"
  curl -fsSL -o "$TMP_TGZ" "$URL_BASE/cloudflared-darwin-$ARCH.tgz"
  tar -xzf "$TMP_TGZ" -C "$TOOLS_DIR"
  rm -f "$TMP_TGZ"
  # The extracted file is named 'cloudflared'
  mv -f "$TOOLS_DIR/cloudflared" "$TARGET"
  chmod +x "$TARGET"
fi

echo "cloudflared available at: $TARGET"


