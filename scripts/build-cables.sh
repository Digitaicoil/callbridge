#!/bin/bash
# Builds the two virtual audio cables CallBridge needs from BlackHole's source (GPL-3.0, github.com/ExistentialAudio/BlackHole).
# CallBridge doesn't ship BlackHole binaries: this builds them on your Mac. Needs Xcode (not just the command line tools).
#   CALLBRIDGE_DEVELOPMENT_TEAM=ABCDE12345 bash scripts/build-cables.sh   (optional: sign with your Apple team; default ad-hoc)
set -euo pipefail
VERSION="${BLACKHOLE_VERSION:-v0.7.1}"
WORK="${CALLBRIDGE_BUILD_DIR:-$HOME/Library/Caches/callbridge/BlackHole}"
command -v xcodebuild >/dev/null || { echo "Xcode is required: install it from the App Store, then: sudo xcode-select -s /Applications/Xcode.app"; exit 1; }
if [ ! -d "$WORK/.git" ]; then
  git clone --quiet --depth 1 --branch "$VERSION" https://github.com/ExistentialAudio/BlackHole.git "$WORK"
fi
cd "$WORK"
SIGN=(CODE_SIGN_IDENTITY="-" CODE_SIGN_STYLE=Manual)
[ -n "${CALLBRIDGE_DEVELOPMENT_TEAM:-}" ] && SIGN=(DEVELOPMENT_TEAM="$CALLBRIDGE_DEVELOPMENT_TEAM" CODE_SIGN_STYLE=Automatic -allowProvisioningUpdates)
for name in CallBridgeCall CallBridgeAgent; do
  bid="audio.callbridge.$name"
  xcodebuild -quiet -project BlackHole.xcodeproj -configuration Release -target BlackHole \
    CONFIGURATION_BUILD_DIR="$WORK/build/$name" PRODUCT_BUNDLE_IDENTIFIER="$bid" "${SIGN[@]}" \
    "GCC_PREPROCESSOR_DEFINITIONS=\$GCC_PREPROCESSOR_DEFINITIONS kNumber_Of_Channels=2 kPlugIn_BundleID=\\\"$bid\\\" kDriver_Name=\\\"$name\\\""
  rm -rf "$WORK/build/$name/$name.driver"
  mv "$WORK/build/$name/BlackHole.driver" "$WORK/build/$name/$name.driver"
  echo "built $name.driver"
done
echo "next: sudo bash scripts/install-cables.sh"
