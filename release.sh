#!/bin/bash
# Release script for Path of Purpose
# Usage: ./release.sh 0.2.0
#
# This script:
# 1. Builds the Python sidecar with Nuitka
# 2. Copies the sidecar to Tauri's binaries/ dir
# 3. Builds the Tauri app with signing
# 4. Generates latest.json for the updater
# 5. Creates a GitHub release with all artifacts

set -e

VERSION="${1:?Usage: ./release.sh <version>}"
REPO="Mancavegaming/path-of-purpose"
BUNDLE_DIR="src-tauri-app/src-tauri/target/release/bundle/nsis"
BINARIES_DIR="src-tauri-app/src-tauri/binaries"

# Signing key config
export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/pathofpurpose.key)"
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD="pop2026"

echo "=== Step 1: Building Python sidecar with Nuitka ==="
cd src-python
python -m nuitka \
    --onefile \
    --output-dir=build \
    --include-package=pop \
    --assume-yes-for-downloads \
    pop/main.py
cd ..

echo "=== Step 2: Copying sidecar to Tauri binaries ==="
cp "src-python/build/main.exe" \
   "${BINARIES_DIR}/pop-engine-x86_64-pc-windows-msvc.exe"
echo "Sidecar size: $(du -h "${BINARIES_DIR}/pop-engine-x86_64-pc-windows-msvc.exe" | cut -f1)"

echo "=== Step 3: Building Path of Purpose v${VERSION} ==="

# Update version in tauri.conf.json
sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION}\"/" src-tauri-app/src-tauri/tauri.conf.json

# Build
cd src-tauri-app
npm run tauri build
cd ..

echo "=== Step 4: Generating latest.json ==="

# Generate latest.json for the updater
SETUP_FILE="${BUNDLE_DIR}/Path of Purpose_${VERSION}_x64-setup.nsis.zip"
SIG_FILE="${SETUP_FILE}.sig"

if [ ! -f "$SIG_FILE" ]; then
    echo "ERROR: Signature file not found: $SIG_FILE"
    echo "Available files in ${BUNDLE_DIR}/:"
    ls -la "${BUNDLE_DIR}/"
    exit 1
fi

SIGNATURE=$(cat "$SIG_FILE")
PUB_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/v${VERSION}/Path.of.Purpose_${VERSION}_x64-setup.nsis.zip"

cat > "${BUNDLE_DIR}/latest.json" << EOF
{
  "version": "${VERSION}",
  "notes": "Path of Purpose v${VERSION}",
  "pub_date": "${PUB_DATE}",
  "platforms": {
    "windows-x86_64": {
      "signature": "${SIGNATURE}",
      "url": "${DOWNLOAD_URL}"
    }
  }
}
EOF

echo "=== Generated latest.json ==="
cat "${BUNDLE_DIR}/latest.json"

echo ""
echo "=== Step 5: Creating GitHub release ==="

# Upload artifacts to GitHub release
gh release create "v${VERSION}" \
    "${BUNDLE_DIR}/Path of Purpose_${VERSION}_x64-setup.exe" \
    "${BUNDLE_DIR}/Path of Purpose_${VERSION}_x64-setup.nsis.zip" \
    "${BUNDLE_DIR}/Path of Purpose_${VERSION}_x64-setup.nsis.zip.sig" \
    "${BUNDLE_DIR}/latest.json" \
    --title "Path of Purpose v${VERSION}" \
    --notes "Path of Purpose v${VERSION} — auto-update release"

echo ""
echo "=== Release v${VERSION} published! ==="
echo "Users will receive the update automatically via Check for Updates."
