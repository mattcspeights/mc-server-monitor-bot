# Security

## Reporting a vulnerability

If you find a security issue, please report it privately rather than opening a public issue.

Contact: open a GitHub security advisory on this repository, or email the maintainer listed in the git history.

## Secrets

Never commit these to git:

- `DISCORD_TOKEN` in `.env`
- Discord channel or role IDs tied to your server (optional, but `.env` should stay local)
- Any Minecraft RCON password (this bot uses `docker compose exec` and does not need RCON in `.env`)

If a bot token is exposed, reset it immediately in the [Discord Developer Portal](https://discord.com/developers/applications) and update your local `.env`.

## Permissions

Users with Discord administrator permission, the server owner, or the role set in `BOOT_ROLE_ID` can start and stop the Minecraft container via `/boot` and `/stop`. Only grant `BOOT_ROLE_ID` to trusted operators.

The bot needs Docker access on the host to run those commands. Run it as a user in the `docker` group only on machines you control.
