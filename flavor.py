"""Sauron-themed bot copy and randomized player flavor text."""

from __future__ import annotations

import random

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
        return "None dare tread Middle-GregTech"
    return format_player_roster(names, avoid=avoid)
