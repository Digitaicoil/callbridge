#!/bin/bash
# Installs the two cables built by build-cables.sh and restarts Core Audio (sound drops for a second).
#   sudo bash scripts/install-cables.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo: sudo bash $0"; exit 1; }
USER_HOME=$(eval echo "~${SUDO_USER:-$USER}")
B="${CALLBRIDGE_BUILD_DIR:-$USER_HOME/Library/Caches/callbridge/BlackHole}/build"
for name in CallBridgeCall CallBridgeAgent; do
  [ -d "$B/$name/$name.driver" ] || { echo "missing $B/$name/$name.driver: run scripts/build-cables.sh first"; exit 1; }
  rm -rf "/Library/Audio/Plug-Ins/HAL/$name.driver"
  cp -R "$B/$name/$name.driver" /Library/Audio/Plug-Ins/HAL/
  chown -R root:wheel "/Library/Audio/Plug-Ins/HAL/$name.driver"
done
killall coreaudiod 2>/dev/null || true
echo "installed: CallBridgeCall 2ch, CallBridgeAgent 2ch"
