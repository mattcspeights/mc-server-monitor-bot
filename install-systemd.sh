#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="gtnh-discord-bot"
BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_TEMPLATE="${BOT_DIR}/gtnh-discord-bot.service.example"
UNIT_DST="/etc/systemd/system/${SERVICE_NAME}.service"
SERVICE_USER="${SUDO_USER:-${USER}}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo bash "$0" "$@"
fi

if [[ ! -x "${BOT_DIR}/.venv/bin/python" ]]; then
  echo "Missing venv. Run:"
  echo "  cd ${BOT_DIR}"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [[ ! -f "${BOT_DIR}/.env" ]]; then
  echo "Missing ${BOT_DIR}/.env"
  echo "  cp .env.example .env"
  echo "  # then fill in DISCORD_TOKEN and STATUS_CHANNEL_ID"
  exit 1
fi

sed -e "s|@BOT_DIR@|${BOT_DIR}|g" \
    -e "s|@SERVICE_USER@|${SERVICE_USER}|g" \
    "${UNIT_TEMPLATE}" > "${UNIT_DST}"
chmod 0644 "${UNIT_DST}"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

pkill -f "${BOT_DIR}/.venv/bin/python bot.py" 2>/dev/null || true
sleep 1

systemctl restart "${SERVICE_NAME}"
systemctl --no-pager status "${SERVICE_NAME}"

echo
echo "Installed and started ${SERVICE_NAME}"
echo "  Unit:    ${UNIT_DST}"
echo "  Logs:    journalctl -u ${SERVICE_NAME} -f"
echo "  Stop:    sudo systemctl stop ${SERVICE_NAME}"
echo "  Restart: sudo systemctl restart ${SERVICE_NAME}"
