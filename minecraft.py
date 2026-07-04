"""Minecraft server status via mcstatus ping and RCON through docker exec."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from mcstatus import JavaServer

logger = logging.getLogger(__name__)

_PLAYER_LIST_RE = re.compile(
    r"^There are (?P<count>\d+)"
    r"(?:/(?P<max_slash>\d+)| of a max(?:imum)? of (?P<max_long>\d+))"
    r" players online:\s*(?P<names>.*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PingStatus:
    online: bool
    motd: str | None = None
    latency_ms: float | None = None
    player_count: int | None = None
    max_players: int | None = None
    player_names: list[str] | None = None
    version: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class PlayerList:
    count: int
    max_players: int
    names: list[str]
    source: str
    error: str | None = None


class MinecraftClient:
    def __init__(
        self,
        host: str,
        port: int,
        compose_dir: Path,
        compose_service: str,
    ) -> None:
        self.host = host
        self.port = port
        self.compose_dir = compose_dir
        self.compose_service = compose_service

    async def ping(self) -> PingStatus:
        server = JavaServer(self.host, self.port)
        try:
            status = await asyncio.to_thread(server.status)
            players = status.players
            motd = status.description
            if not isinstance(motd, str):
                motd = str(motd)

            sample_names = [player.name for player in players.sample or [] if player.name]

            return PingStatus(
                online=True,
                motd=motd,
                latency_ms=status.latency,
                player_count=players.online,
                max_players=players.max,
                player_names=sample_names,
                version=status.version.name if status.version else None,
            )
        except Exception as exc:
            logger.debug("mcstatus ping failed: %s", exc)
            return PingStatus(online=False, error=str(exc))

    async def list_players(self) -> PlayerList:
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "compose",
            "exec",
            "-T",
            self.compose_service,
            "rcon-cli",
            "list",
            cwd=self.compose_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return PlayerList(0, 0, [], "rcon", "RCON timed out")

        output = stdout.decode().strip()
        err = stderr.decode().strip()
        if proc.returncode != 0:
            return PlayerList(0, 0, [], "rcon", err or output or "RCON failed")

        match = _PLAYER_LIST_RE.match(output)
        if not match:
            return PlayerList(0, 0, [], "rcon", f"Unexpected RCON output: {output}")

        max_players = match.group("max_slash") or match.group("max_long")
        names_raw = match.group("names").strip()
        names = [name.strip() for name in names_raw.split(",") if name.strip()]
        return PlayerList(
            count=int(match.group("count")),
            max_players=int(max_players),
            names=names,
            source="rcon",
        )

    async def get_online_players(self) -> PlayerList:
        players = await self.list_players()
        if not players.error and (players.names or players.count == 0):
            return players

        ping = await self.ping()
        if not ping.online:
            return players if players.error else PlayerList(0, 0, [], "offline")

        names = ping.player_names or []
        count = players.count if not players.error else (ping.player_count or len(names))
        max_players = players.max_players if not players.error else (ping.max_players or 20)
        if count == 0:
            return PlayerList(0, max_players, [], "ping")

        if names:
            return PlayerList(count, max_players, names, "ping")

        return PlayerList(count, max_players, [], "ping", "Player names unavailable")
