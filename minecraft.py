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

_MC_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,16}$")

_WHITELIST_REJECT_RES: tuple[re.Pattern[str], ...] = (
    # Modern Paper/Spigot: GameProfile with name=Username
    re.compile(
        r"name=(?P<player>[A-Za-z0-9_]{3,16}).*not white-?listed",
        re.IGNORECASE,
    ),
    # Legacy: username before IP parens
    re.compile(
        r"(?P<player>[A-Za-z0-9_]{3,16})\s*\([^)]*\)\s*lost connection:\s*"
        r"You are not white-?listed",
        re.IGNORECASE,
    ),
    re.compile(
        r"Disconnecting\s+(?P<player>[A-Za-z0-9_]{3,16}):\s*You are not white-?listed",
        re.IGNORECASE,
    ),
    re.compile(
        r"GameProfile@[^\]]+\[(?P<player>[A-Za-z0-9_]{3,16})\].*not white-?listed",
        re.IGNORECASE,
    ),
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


@dataclass(frozen=True)
class RconResult:
    ok: bool
    output: str
    error: str | None = None


def is_valid_mc_username(username: str) -> bool:
    return bool(_MC_USERNAME_RE.match(username))


def parse_whitelist_rejection(line: str) -> str | None:
    for pattern in _WHITELIST_REJECT_RES:
        match = pattern.search(line)
        if match:
            return match.group("player")
    return None


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

    async def run_rcon(self, *args: str, timeout: float = 15.0) -> RconResult:
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "compose",
            "exec",
            "-T",
            self.compose_service,
            "rcon-cli",
            *args,
            cwd=self.compose_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return RconResult(False, "", "RCON timed out")

        output = stdout.decode().strip()
        err = stderr.decode().strip()
        if proc.returncode != 0:
            return RconResult(False, output, err or output or "RCON failed")
        return RconResult(True, output)

    async def whitelist_add(self, username: str) -> RconResult:
        return await self.run_rcon("whitelist", "add", username)

    async def list_players(self) -> PlayerList:
        result = await self.run_rcon("list")
        if not result.ok:
            return PlayerList(0, 0, [], "rcon", result.error or result.output or "RCON failed")

        output = result.output
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
