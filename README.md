# MC Server Monitor Bot

Discord bot for monitoring a Minecraft server running in Docker ([`itzg/minecraft-server`](https://hub.docker.com/r/itzg/minecraft-server)), with an auto-updating status embed, slash commands, and optional remote boot/stop.

Built for a GregTech: New Horizons setup and ships with LotR-themed copy and player flavor text. The monitoring and Docker control logic works with any similar Compose-based Java server; customize the messages in `flavor.py` and `status_embed.py` if you want a different theme.

## Features

- Live status embed (container state, ping, players, MOTD)
- `/status`, `/players`, `/boot`, `/stop` slash commands
- Optional periodic channel purge (keeps only the embed)
- systemd user or system service install scripts

## Requirements

- Python 3.10+
- Docker and Docker Compose on the host
- A Discord application with bot token and slash commands enabled

## Quick start

See [SETUP.md](SETUP.md) for full instructions.

```bash
git clone https://github.com/mattcspeights/mc-server-monitor-bot.git
cd mc-server-monitor-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env, then:
python bot.py
```

## Security

See [SECURITY.md](SECURITY.md) for reporting issues and handling secrets.

## License

MIT — see [LICENSE](LICENSE).
