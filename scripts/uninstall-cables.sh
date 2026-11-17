#!/bin/bash
# Removes the CallBridge cables.   sudo bash scripts/uninstall-cables.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo: sudo bash $0"; exit 1; }
rm -rf /Library/Audio/Plug-Ins/HAL/CallBridgeCall.driver /Library/Audio/Plug-Ins/HAL/CallBridgeAgent.driver
killall coreaudiod 2>/dev/null || true
echo "removed"
