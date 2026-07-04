#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="gtnh-discord-bot"
BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_TEMPLATE="${BOT_DIR}/gtnh-discord-bot.user.service.example"
USER_UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_DST="${USER_UNIT_DIR}/${SERVICE_NAME}.service"

if [[ ! -x "${BOT_DIR}/.venv/bin/python" ]]; then
  echo "Missing venv. Run:"
  echo "  cd ${BOT_DIR}"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [[ ! -f "${BOT_DIR}/.env" ]]; then
  echo "Missing ${BOT_DIR}/.env"
  exit 1
fi

mkdir -p "${USER_UNIT_DIR}"
sed "s|@BOT_DIR@|${BOT_DIR}|g" "${UNIT_TEMPLATE}" > "${UNIT_DST}"
chmod 0644 "${UNIT_DST}"

systemctl --user daemon-reload
systemctl --user enable "${SERVICE_NAME}"

if command -v loginctl >/dev/null 2>&1; then
  loginctl enable-linger "${USER}" 2>/dev/null || true
fi

pkill -f "${BOT_DIR}/.venv/bin/python bot.py" 2>/dev/null || true
sleep 1

systemctl --user restart "${SERVICE_NAME}"
systemctl --user --no-pager status "${SERVICE_NAME}"

echo
echo "Installed user service ${SERVICE_NAME}"
echo "  Unit:    ${UNIT_DST}"
echo "  Logs:    journalctl --user -u ${SERVICE_NAME} -f"
echo "  Stop:    systemctl --user stop ${SERVICE_NAME}"
echo "  Restart: systemctl --user restart ${SERVICE_NAME}"
