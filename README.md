# MC Server Monitor Bot

Discord bot for monitoring a GTNH Minecraft server (Docker + `itzg/minecraft-server`), with an auto-updating status embed, slash commands, and optional remote boot/stop.

## Features

- Live status embed (container state, ping, players, MOTD)
- `/status`, `/players`, `/boot`, `/stop` slash commands
- Sauron-themed messages with randomized player flavor text
- Optional periodic channel purge (keeps only the embed)
- systemd user or system service install scripts

## Quick start

See [SETUP.md](SETUP.md) for full instructions.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env, then:
python bot.py
```

## License

Private / personal use unless otherwise specified.
