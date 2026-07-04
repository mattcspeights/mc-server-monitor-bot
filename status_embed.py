"""Build the GTNH server status Discord embed."""

from __future__ import annotations

from datetime import datetime, timezone

import discord

from docker_control import ContainerState, ComposeStatus
from flavor import format_player_report
from minecraft import PingStatus, PlayerList


def _container_label(state: ContainerState) -> str:
    return {
        ContainerState.RUNNING: "The furnaces burn",
        ContainerState.STOPPED: "Barad-dûr sleeps",
        ContainerState.STARTING: "The Eye stirs",
        ContainerState.UNKNOWN: "Shrouded in shadow",
    }[state]


def _game_label(online: bool) -> str:
    return "The Eye is open" if online else "The Eye is closed"


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
        return "None dare tread Middle-GregTech"

    return "The eye reveals nothing"


def build_status_embed(
    compose: ComposeStatus,
    ping: PingStatus,
    players: PlayerList | None,
    *,
    server_hostname: str,
    server_port: int,
    avoid_roster: str | None = None,
) -> discord.Embed:
    online = ping.online and compose.state == ContainerState.RUNNING
    color = discord.Color.dark_red() if online else discord.Color.dark_grey()

    embed = discord.Embed(
        title="👁 The Eye Upon GregTech: New Horizons",
        description=(
            "One modpack to rule them all, and in the darkness bind them.\n"
            f"**Road to Mordor:** `{server_hostname}`"
        ),
        color=color,
        timestamp=datetime.now(timezone.utc),
    )

    embed.add_field(
        name="Barad-dûr (Container)",
        value=_container_label(compose.state),
        inline=True,
    )
    embed.add_field(
        name="The Great Eye (Server)",
        value=_game_label(ping.online),
        inline=True,
    )
    embed.add_field(
        name="Servants in Mordor",
        value=_players_text(players, ping, avoid_roster=avoid_roster),
        inline=False,
    )

    if ping.motd:
        embed.add_field(name="Words Upon the Gate", value=ping.motd[:1024], inline=False)

    stats: list[tuple[str, str]] = []
    if ping.latency_ms is not None:
        stats.append(("Delay", f"{ping.latency_ms:.0f} ms"))
    if ping.version:
        stats.append(("Age of the World", ping.version))

    for index, (name, value) in enumerate(stats):
        embed.add_field(name=name, value=value, inline=len(stats) > 1)

    if compose.status_text:
        embed.set_footer(text=compose.status_text[:2048])

    return embed
