#!/bin/bash
# Release script for Path of Purpose
# Usage: ./release.sh 0.2.0
#
# This script:
# 1. Builds the app with signing
# 2. Generates latest.json for the updater
# 3. Creates a GitHub release with all artifacts

set -e

VERSION="${1:?Usage: ./release.sh <version>}"
REPO="Mancavegaming/path-of-purpose"
BUNDLE_DIR="src-tauri-app/src-tauri/target/release/bundle/nsis"

# Signing key config
export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/pathofpurpose.key)"
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD="pop2026"

echo "=== Building Path of Purpose v${VERSION} ==="

# Update version in tauri.conf.json
sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION}\"/" src-tauri-app/src-tauri/tauri.conf.json

# Build
cd src-tauri-app
npm run tauri build
cd ..

echo "=== Build complete ==="

# Generate latest.json for the updater
SETUP_FILE="${BUNDLE_DIR}/Path of Purpose_${VERSION}_x64-setup.nsis.zip"
SIG_FILE="${SETUP_FILE}.sig"

if [ ! -f "$SIG_FILE" ]; then
    echo "ERROR: Signature file not found: $SIG_FILE"
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
echo "=== Artifacts ready in ${BUNDLE_DIR}/ ==="
echo ""
echo "To create the GitHub release, run:"
echo ""
echo "  gh release create v${VERSION} \\"
echo "    \"${BUNDLE_DIR}/Path of Purpose_${VERSION}_x64-setup.exe\" \\"
echo "    \"${BUNDLE_DIR}/Path of Purpose_${VERSION}_x64-setup.nsis.zip\" \\"
echo "    \"${BUNDLE_DIR}/Path of Purpose_${VERSION}_x64-setup.nsis.zip.sig\" \\"
echo "    \"${BUNDLE_DIR}/latest.json\" \\"
echo "    --title \"Path of Purpose v${VERSION}\" \\"
echo "    --notes \"Auto-update release\""
echo ""
