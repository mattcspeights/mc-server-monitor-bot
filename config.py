"""Load bot configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_BOT_DIR = Path(__file__).resolve().parent
_DEFAULT_COMPOSE_DIR = _BOT_DIR.parent


@dataclass(frozen=True)
class Config:
    discord_token: str
    status_channel_id: int
    ADMIN_ROLE_ID: int | None
    refresh_interval_seconds: int
    mc_host: str
    mc_port: int
    mc_hostname: str
    compose_dir: Path
    compose_service: str
    boot_timeout_seconds: int
    channel_purge_interval_seconds: int
    state_file: Path


def load_config() -> Config:
    load_dotenv(_BOT_DIR / ".env")

    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise ValueError("DISCORD_TOKEN is required in .env")

    status_channel_id = int(os.getenv("STATUS_CHANNEL_ID", "0"))
    if status_channel_id <= 0:
        raise ValueError("STATUS_CHANNEL_ID is required in .env")

    boot_role_raw = os.getenv("ADMIN_ROLE_ID", "").strip()
    ADMIN_ROLE_ID = int(boot_role_raw) if boot_role_raw else None

    return Config(
        discord_token=token,
        status_channel_id=status_channel_id,
        ADMIN_ROLE_ID=ADMIN_ROLE_ID,
        refresh_interval_seconds=int(os.getenv("REFRESH_INTERVAL_SECONDS", "180")),
        mc_host=os.getenv("MC_HOST", "127.0.0.1"),
        mc_port=int(os.getenv("MC_PORT", "25565")),
        mc_hostname=os.getenv("MC_HOSTNAME", "minecraft.example.com").strip(),
        compose_dir=Path(os.getenv("COMPOSE_DIR", str(_DEFAULT_COMPOSE_DIR))),
        compose_service=os.getenv("COMPOSE_SERVICE", "mc"),
        boot_timeout_seconds=int(os.getenv("BOOT_TIMEOUT_SECONDS", "900")),
        channel_purge_interval_seconds=int(
            os.getenv("CHANNEL_PURGE_INTERVAL_SECONDS", "3600")
        ),
        state_file=_BOT_DIR / "status_state.json",
    )
