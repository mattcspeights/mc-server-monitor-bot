#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="gtnh-discord-bot"
BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_DST="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo bash "$0" "$@"
fi

echo "Uninstalling system service ${SERVICE_NAME}..."

if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
  systemctl stop "${SERVICE_NAME}"
fi

if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
  systemctl disable "${SERVICE_NAME}"
fi

rm -f "${UNIT_DST}"
systemctl daemon-reload
systemctl reset-failed "${SERVICE_NAME}" 2>/dev/null || true

pkill -f "${BOT_DIR}/.venv/bin/python bot.py" 2>/dev/null || true

echo
echo "Uninstalled ${SERVICE_NAME}"
echo "  Removed unit: ${UNIT_DST}"
echo
echo "The bot code in ${BOT_DIR} was not deleted."
echo "To reinstall: ./install-systemd.sh"
