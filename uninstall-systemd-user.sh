#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="gtnh-discord-bot"
BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_DST="${USER_UNIT_DIR}/${SERVICE_NAME}.service"
ENABLE_LINK="${USER_UNIT_DIR}/default.target.wants/${SERVICE_NAME}.service"

echo "Uninstalling user service ${SERVICE_NAME}..."

if systemctl --user is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
  systemctl --user stop "${SERVICE_NAME}"
fi

if systemctl --user is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
  systemctl --user disable "${SERVICE_NAME}"
fi

rm -f "${UNIT_DST}" "${ENABLE_LINK}"
systemctl --user daemon-reload
systemctl --user reset-failed "${SERVICE_NAME}" 2>/dev/null || true

pkill -f "${BOT_DIR}/.venv/bin/python bot.py" 2>/dev/null || true

echo
echo "Uninstalled ${SERVICE_NAME}"
echo "  Removed unit: ${UNIT_DST}"
echo
echo "The bot code in ${BOT_DIR} was not deleted."
echo "To reinstall: ./install-systemd-user.sh"
