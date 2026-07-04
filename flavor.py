"""Themed messaging config — customize all user-facing text here."""

from __future__ import annotations

import random

# --- Slash command descriptions ---

CMD_STATUS_DESC = "Show current GTNH server status"
CMD_PLAYERS_DESC = "List online players"
CMD_BOOT_DESC = "Start the GTNH server container (admin only)"
CMD_STOP_DESC = "Stop the GTNH server container (admin only)"

# --- Status embed ---

EMBED_TITLE = "👁 The Eye Upon GregTech: New Horizons"
EMBED_DESCRIPTION_TEMPLATE = (
    "One modpack to rule them all, and in the darkness bind them.\n"
    "**Road to Mordor:** `{hostname}`"
)

EMBED_FIELD_CONTAINER = "Barad-dûr (Container)"
EMBED_FIELD_SERVER = "The Great Eye (Server)"
EMBED_FIELD_PLAYERS = "Servants in Mordor"
EMBED_FIELD_MOTD = "Words Upon the Gate"
EMBED_FIELD_LATENCY = "Delay"
EMBED_FIELD_VERSION = "Age of the World"

CONTAINER_LABELS: dict[str, str] = {
    "running": "The furnaces burn",
    "stopped": "Barad-dûr sleeps",
    "starting": "The Eye stirs",
    "unknown": "Shrouded in shadow",
}

GAME_LABEL_ONLINE = "The Eye is open"
GAME_LABEL_OFFLINE = "The Eye is closed"

EMPTY_PLAYERS = "None dare tread Middle-GregTech"
PLAYERS_UNKNOWN = "The eye reveals nothing"

# --- Player roster flavor ---

PLAYER_FLAVOR_TEMPLATES: tuple[str, ...] = (
    "{user} is greggin' it up",
    "{user} has been consumed by the One Router",
    "{user} stares into the NEI search bar, unblinking",
    "{user} is one gauge away from insanity",
    "{user} whispers 'just one more quest' to the void",
    "{user} has achieved MV and immediately regretted it",
    "{user} is brewing tea for the Blood Magic altar",
    "{user} is lost in the End — send help",
    "{user} is micromanaging a single steam boiler",
    "{user} has stood in the same chunk for six hours",
    "{user} is manufacturing 576 coke ovens",
)


def embed_description(hostname: str) -> str:
    return EMBED_DESCRIPTION_TEMPLATE.format(hostname=hostname)


def container_label(state: str) -> str:
    return CONTAINER_LABELS[state]


def game_label(online: bool) -> str:
    return GAME_LABEL_ONLINE if online else GAME_LABEL_OFFLINE


def player_flavor_line(username: str, templates: list[str] | None = None) -> str:
    pool = templates or list(PLAYER_FLAVOR_TEMPLATES)
    template = random.choice(pool)
    return template.format(user=username)


def format_player_roster(names: list[str], *, avoid: str | None = None) -> str:
    if not names:
        return ""

    for _ in range(8):
        templates = list(PLAYER_FLAVOR_TEMPLATES)
        random.shuffle(templates)
        lines = []
        for index, name in enumerate(names):
            template = templates[index % len(templates)]
            lines.append(f"• {template.format(user=name)}")
        roster = "\n".join(lines)
        if avoid is None or roster != avoid:
            return roster

    return roster


def format_player_report(
    count: int,
    max_players: int,
    names: list[str],
    *,
    avoid: str | None = None,
) -> str:
    if count == 0 or not names:
        return EMPTY_PLAYERS
    return format_player_roster(names, avoid=avoid)


# --- /players command ---

def msg_server_down() -> str:
    return "The Eye closes. Barad-dûr sleeps in silence — the server is down."


def msg_players_error(error: str) -> str:
    return f"The furnace flickers. Their names are lost to shadow: {error}"


def msg_no_players() -> str:
    return "The lands of Mordor lie empty. None dare tread Middle-GregTech."


def msg_players_roster(count: int, max_players: int, roster: str) -> str:
    return f"**{count}/{max_players}** servants labor in the darkness:\n{roster}"


# --- /boot command ---

def msg_boot_denied() -> str:
    return "You dare command the Dark Lord's forge? Begone, halfling."


def msg_boot_already_online() -> str:
    return "The Black Gate already stands open, fool. The server is online."


def msg_boot_start_failed(message: str) -> str:
    return f"The flames of Mount Doom sputter. The server rejects your will: {message}"


def msg_boot_already_running() -> str:
    return (
        "The furnaces of Barad-dûr already burn. The Eye has not yet opened — "
        "GregTech loads at its own pace."
    )


def msg_boot_starting() -> str:
    return (
        "The furnaces of Barad-dûr ignite... Patience, mortal. "
        "GregTech loads at its own pace."
    )


def msg_boot_ready() -> str:
    return "Rise. The Eye opens. The server breathes once more."


def msg_boot_timeout() -> str:
    return (
        "The container stirs, yet the world remains blind. "
        "The mods still slumber in darkness — give it more time."
    )


# --- /stop command ---

def msg_stop_denied() -> str:
    return "Only the Dark Lord may quench the forges. You are not worthy."


def msg_stop_already_stopped() -> str:
    return "Barad-dûr is already ash. There is nothing left to extinguish."


def msg_stop_failed(message: str) -> str:
    return f"Even the Dark Lord cannot halt the machine: {message}"


def msg_stop_success() -> str:
    return "Let the forges cool. The server returns to shadow."
