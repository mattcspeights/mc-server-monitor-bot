"""Build the GTNH server status Discord embed."""

from __future__ import annotations

from datetime import datetime, timezone

import discord

from docker_control import ContainerState, ComposeStatus
from flavor import (
    EMBED_FIELD_CONTAINER,
    EMBED_FIELD_LATENCY,
    EMBED_FIELD_MOTD,
    EMBED_FIELD_PLAYERS,
    EMBED_FIELD_SERVER,
    EMBED_FIELD_VERSION,
    EMBED_TITLE,
    EMPTY_PLAYERS,
    PLAYERS_UNKNOWN,
    container_label,
    embed_description,
    format_player_report,
    game_label,
)
from minecraft import PingStatus, PlayerList


def _players_text(
    players: PlayerList | None,
    ping: PingStatus,
    *,
    avoid_roster: str | None = None,
) -> str:
    if players and not players.error:
        return format_player_report(
            players.count, players.max_players, players.names, avoid=avoid_roster
        )

    if players and players.error and players.names:
        return format_player_report(
            players.count, players.max_players, players.names, avoid=avoid_roster
        )

    if ping.player_names:
        count = ping.player_count or len(ping.player_names)
        max_players = ping.max_players or 20
        return format_player_report(count, max_players, ping.player_names, avoid=avoid_roster)

    if ping.online and ping.player_count == 0:
        return EMPTY_PLAYERS

    return PLAYERS_UNKNOWN


def build_status_embed(
    compose: ComposeStatus,
    ping: PingStatus,
    players: PlayerList | None,
    *,
    mc_hostname: str,
    server_port: int,
    avoid_roster: str | None = None,
) -> discord.Embed:
    online = ping.online and compose.state == ContainerState.RUNNING
    color = discord.Color.dark_red() if online else discord.Color.dark_grey()

    embed = discord.Embed(
        title=EMBED_TITLE,
        description=embed_description(mc_hostname),
        color=color,
        timestamp=datetime.now(timezone.utc),
    )

    embed.add_field(
        name=EMBED_FIELD_CONTAINER,
        value=container_label(compose.state.value),
        inline=True,
    )
    embed.add_field(
        name=EMBED_FIELD_SERVER,
        value=game_label(ping.online),
        inline=True,
    )
    embed.add_field(
        name=EMBED_FIELD_PLAYERS,
        value=_players_text(players, ping, avoid_roster=avoid_roster),
        inline=False,
    )

    if ping.motd:
        embed.add_field(name=EMBED_FIELD_MOTD, value=ping.motd[:1024], inline=False)

    stats: list[tuple[str, str]] = []
    if ping.latency_ms is not None:
        stats.append((EMBED_FIELD_LATENCY, f"{ping.latency_ms:.0f} ms"))
    if ping.version:
        stats.append((EMBED_FIELD_VERSION, ping.version))

    for index, (name, value) in enumerate(stats):
        embed.add_field(name=name, value=value, inline=len(stats) > 1)

    if compose.status_text:
        embed.set_footer(text=compose.status_text[:2048])

    return embed
