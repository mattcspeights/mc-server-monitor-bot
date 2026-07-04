# MC Server Monitor Bot — Setup

## 1. Discord application

1. Create an app at https://discord.com/developers/applications
2. Add a bot and copy the token into `.env` as `DISCORD_TOKEN`
3. Invite the bot with scopes `bot` and `applications.commands`
4. Permissions: Send Messages, Embed Links, Use Slash Commands
5. Create a status channel (for example `#server-status`) and set `STATUS_CHANNEL_ID` in `.env`
6. **Give the bot access to that channel** (required for the status embed):
   - Right-click the channel → **Edit Channel** → **Permissions**
   - Click **+** → add your bot
   - Enable **View Channel**, **Send Messages**, **Embed Links**, **Read Message History**
   - Enable **Manage Messages** if you use channel purge (see `CHANNEL_PURGE_INTERVAL_SECONDS`)
   - If the channel is in a category, repeat for the **category** if needed
7. Optionally create an admin role and set `ADMIN_ROLE_ID` (administrator permission also works)

## 2. Install dependencies

```bash
cd mc-server-monitor-bot   # your clone directory
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your values
```

## 3. Run manually (test)

```bash
source .venv/bin/activate
python bot.py
```

## 4. Run as a systemd service (recommended)

Use systemd so the bot starts on boot, restarts on failure, and is easy to manage with `systemctl`.

### Prerequisites

Complete sections 1–2 first:

- `.venv` exists with dependencies installed
- `.env` is configured
- Your user is in the `docker` group (for `/boot` and `/stop`):

```bash
groups
# should include: docker
```

### Option A: user service (recommended, no sudo)

Best for running as your own user. The install script enables **linger** so the bot keeps running after reboot even without an active login session.

**Install and start:**

```bash
cd mc-server-monitor-bot   # your clone directory
./install-systemd-user.sh
```

This script:

1. Renders `gtnh-discord-bot.user.service.example` with your install path
2. Installs the unit to `~/.config/systemd/user/`
3. Enables the service on boot
4. Enables linger for your user
5. Stops any manually running `python bot.py` process
6. Starts the service

**Verify it is running:**

```bash
systemctl --user is-active gtnh-discord-bot
# expect: active

systemctl --user status gtnh-discord-bot
# expect: Active: active (running)
```

**View logs:**

```bash
journalctl --user -u gtnh-discord-bot -f
```

Look for:

```text
Logged in as YourBot#1234 (...)
Status channel ready: #server-status (...)
```

**Restart the bot** (required after editing `.env` or pulling code changes):

```bash
systemctl --user restart gtnh-discord-bot
```

**Other useful commands:**

```bash
systemctl --user start gtnh-discord-bot    # start if stopped
systemctl --user stop gtnh-discord-bot     # take offline in Discord
systemctl --user disable gtnh-discord-bot  # stop auto-start on boot
```

**Re-install** after moving the repo or changing install location:

```bash
cd mc-server-monitor-bot
./install-systemd-user.sh
```

**Uninstall** the user service (stops the bot, removes the unit file):

```bash
cd mc-server-monitor-bot
./uninstall-systemd-user.sh
```

### Option B: system service (sudo)

Runs as a system unit under `/etc/systemd/system/`. Use this if you prefer a machine-wide service.

**Install and start:**

```bash
cd mc-server-monitor-bot
./install-systemd.sh
```

**Verify, logs, and restart:**

```bash
sudo systemctl is-active gtnh-discord-bot
sudo systemctl status gtnh-discord-bot
journalctl -u gtnh-discord-bot -f
sudo systemctl restart gtnh-discord-bot   # after .env or code changes
sudo systemctl stop gtnh-discord-bot
```

**Uninstall** the system service:

```bash
cd mc-server-monitor-bot
./uninstall-systemd.sh
```

The service runs as your user with the `docker` group so `/boot` and `/stop` can run `docker compose`.

### When to restart

Restart whenever you change:

- `.env` (token, channel ID, intervals, hostname, etc.)
- Python code in the repository
- The systemd unit file

You do **not** need to restart for Minecraft server start/stop — the bot polls status automatically.

### Troubleshooting

| Problem | What to check |
|---------|----------------|
| `inactive` or `failed` | `journalctl --user -u gtnh-discord-bot -n 50` |
| Bot offline in Discord | `systemctl --user status gtnh-discord-bot` |
| `/boot` permission denied | Discord admin / owner / `ADMIN_ROLE_ID` |
| Missing Access on channel | Bot channel permissions (View Channel, etc.) |
| Purge not working | Bot needs **Manage Messages** on the status channel |
| Two bots running | Stop manual runs: `pkill -f ".venv/bin/python bot.py"` then restart the service |

## Environment variables

See `.env.example` for all options. Secrets (`DISCORD_TOKEN`) must never be committed to git.

`MC_HOSTNAME` is the public address shown in the status embed.

RCON is accessed via `docker compose exec -T mc rcon-cli list` inside the container, so you do not need to expose port 25575 or put the RCON password in the bot `.env`.
