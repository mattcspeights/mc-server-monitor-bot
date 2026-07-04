"""GTNH Discord bot — server status monitoring and admin boot control."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import discord
from discord import app_commands

from config import Config, load_config
from docker_control import ContainerState, DockerControl
from minecraft import MinecraftClient
from flavor import format_player_report
from status_embed import build_status_embed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("gtnh-bot")


class GTNHBot(discord.Client):
    def __init__(self, config: Config) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.config = config
        self.tree = app_commands.CommandTree(self)
        self.docker = DockerControl(config.compose_dir, config.compose_service)
        self.minecraft = MinecraftClient(
            config.mc_host,
            config.mc_port,
            config.compose_dir,
            config.compose_service,
        )
        self._refresh_task: asyncio.Task[None] | None = None
        self._purge_task: asyncio.Task[None] | None = None
        self._logged_channel_access_error = False
        self._logged_purge_permission_error = False
        self._last_embed_roster: str | None = None

    async def setup_hook(self) -> None:
        self._register_commands()
        await self.tree.sync()
        self._refresh_task = asyncio.create_task(self._status_refresh_loop())
        if self.config.channel_purge_interval_seconds > 0:
            self._purge_task = asyncio.create_task(self._channel_purge_loop())

    def _register_commands(self) -> None:
        @self.tree.command(name="status", description="Show current GTNH server status")
        async def status(interaction: discord.Interaction) -> None:
            await interaction.response.defer(thinking=True)
            embed = await self._gather_status_embed()
            await interaction.followup.send(embed=embed)

        @self.tree.command(name="players", description="List online players")
        async def players(interaction: discord.Interaction) -> None:
            await interaction.response.defer(thinking=True)
            compose = await self.docker.get_status()
            if compose.state != ContainerState.RUNNING:
                await interaction.followup.send(
                    "The Eye closes. Barad-dûr sleeps in silence — the server is down."
                )
                return

            player_list = await self.minecraft.get_online_players()
            if player_list.error and not player_list.names:
                await interaction.followup.send(
                    f"The furnace flickers. Their names are lost to shadow: {player_list.error}"
                )
                return

            if player_list.count == 0 or not player_list.names:
                await interaction.followup.send(
                    "The lands of Mordor lie empty. None dare tread Middle-GregTech."
                )
                return

            roster = format_player_report(
                player_list.count,
                player_list.max_players,
                player_list.names,
            )
            await interaction.followup.send(
                f"**{player_list.count}/{player_list.max_players}** servants labor in the darkness:\n{roster}"
            )

        @self.tree.command(name="boot", description="Start the GTNH server container (admin only)")
        async def boot(interaction: discord.Interaction) -> None:
            if not await self._is_admin(interaction):
                await interaction.response.send_message(
                    "You dare command the Dark Lord's forge? Begone, halfling.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(thinking=True)
            compose = await self.docker.get_status()
            if compose.state == ContainerState.RUNNING:
                ping = await self.minecraft.ping()
                if ping.online:
                    await interaction.followup.send(
                        "The Black Gate already stands open, fool. The server is online."
                    )
                    return

            logger.info("Boot requested by user %s (%s)", interaction.user, interaction.user.id)
            ok, message = await self.docker.start()
            if not ok:
                await interaction.followup.send(
                    f"The flames of Mount Doom sputter. The server rejects your will: {message}"
                )
                return

            await interaction.followup.send(
                "The furnaces of Barad-dûr ignite... Patience, mortal. "
                "GregTech loads at its own pace."
            )

            ready = await self._wait_for_ping(self.config.boot_timeout_seconds)
            if ready:
                await interaction.followup.send(
                    "Rise. The Eye opens. The server breathes once more."
                )
            else:
                await interaction.followup.send(
                    "The container stirs, yet the world remains blind. "
                    "The mods still slumber in darkness — give it more time."
                )

            await self._update_status_message()

        @self.tree.command(name="stop", description="Stop the GTNH server container (admin only)")
        async def stop(interaction: discord.Interaction) -> None:
            if not await self._is_admin(interaction):
                await interaction.response.send_message(
                    "Only the Dark Lord may quench the forges. You are not worthy.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(thinking=True)
            compose = await self.docker.get_status()
            if compose.state == ContainerState.STOPPED:
                await interaction.followup.send(
                    "Barad-dûr is already ash. There is nothing left to extinguish."
                )
                return

            logger.info("Stop requested by user %s (%s)", interaction.user, interaction.user.id)
            ok, message = await self.docker.stop()
            if not ok:
                await interaction.followup.send(
                    f"Even the Dark Lord cannot halt the machine: {message}"
                )
                return

            await interaction.followup.send("Let the forges cool. The server returns to shadow.")
            await self._update_status_message()

    async def _is_admin(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.user is None:
            logger.info("Permission denied: command used outside a server")
            return False

        user_id = interaction.user.id

        # Server owner always has full control, regardless of nicknames or roles.
        if interaction.guild.owner_id == user_id:
            return True

        # Discord resolves channel/guild permissions on the interaction payload.
        if interaction.permissions.administrator:
            return True

        role_ids = self._interaction_role_ids(interaction)
        if self.config.boot_role_id and self.config.boot_role_id in role_ids:
            return True

        logger.info(
            "Permission denied for %s (%s): roles=%s boot_role_id=%s "
            "interaction_admin=%s guild_owner_id=%s",
            interaction.user.display_name,
            user_id,
            role_ids,
            self.config.boot_role_id,
            interaction.permissions.administrator,
            interaction.guild.owner_id,
        )
        return False

    def _interaction_role_ids(self, interaction: discord.Interaction) -> list[int]:
        member = interaction.user
        if isinstance(member, discord.Member) and member.roles:
            return [role.id for role in member.roles]

        payload = interaction.data or {}
        member_payload = payload.get("member") or {}
        roles = member_payload.get("roles") or []
        return [int(role_id) for role_id in roles]

    async def _gather_status_embed(self) -> discord.Embed:
        compose = await self.docker.get_status()
        ping = await self.minecraft.ping()
        players = None
        if compose.state == ContainerState.RUNNING:
            players = await self.minecraft.get_online_players()
        embed = build_status_embed(
            compose,
            ping,
            players,
            server_hostname=self.config.server_hostname,
            server_port=self.config.mc_port,
            avoid_roster=self._last_embed_roster,
        )
        for field in embed.fields:
            if field.name == "Servants in Mordor":
                self._last_embed_roster = field.value
                break
        return embed

    async def _wait_for_ping(self, timeout_seconds: int) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while loop.time() < deadline:
            ping = await self.minecraft.ping()
            if ping.online:
                return True
            await asyncio.sleep(15)
        return False

    async def _channel_purge_loop(self) -> None:
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(self.config.channel_purge_interval_seconds)
            try:
                await self._purge_status_channel()
            except Exception:
                logger.exception("Channel purge failed")

    async def _purge_status_channel(self) -> None:
        channel = await self._get_status_channel()
        if channel is None:
            return

        keep_id = self._load_status_message_id()
        if keep_id is None:
            logger.debug("Skipping channel purge: no status embed message yet")
            return

        permissions = channel.permissions_for(channel.guild.me)
        if not permissions.manage_messages:
            self._log_purge_permission_help()
            return

        def should_delete(message: discord.Message) -> bool:
            return message.id != keep_id

        try:
            deleted = await channel.purge(
                check=should_delete,
                limit=None,
                oldest_first=True,
            )
        except discord.Forbidden:
            self._log_purge_permission_help()
            return
        except discord.HTTPException:
            logger.exception("Failed to purge status channel %s", channel.id)
            return

        if deleted:
            logger.info(
                "Purged %s message(s) from #%s; kept status embed %s",
                len(deleted),
                channel.name,
                keep_id,
            )

    def _log_purge_permission_help(self) -> None:
        if self._logged_purge_permission_error:
            return
        self._logged_purge_permission_error = True
        logger.error(
            "Channel purge needs Manage Messages on STATUS_CHANNEL_ID %s. "
            "Edit the channel permissions for the bot role and enable it.",
            self.config.status_channel_id,
        )

    async def _status_refresh_loop(self) -> None:
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await self._update_status_message()
            except Exception:
                logger.exception("Status refresh failed")
            await asyncio.sleep(self.config.refresh_interval_seconds)

    def _log_channel_access_help(self) -> None:
        if self._logged_channel_access_error:
            return
        self._logged_channel_access_error = True
        logger.error(
            "The bot cannot access STATUS_CHANNEL_ID %s (Missing Access). "
            "In Discord: open that text channel -> Edit Channel -> Permissions -> "
            "add the bot role -> enable View Channel, Send Messages, Embed Links, "
            "and Read Message History. If the channel is under a category, check "
            "category permissions too. Confirm the channel ID is from this server.",
            self.config.status_channel_id,
        )

    async def _get_status_channel(self) -> discord.TextChannel | None:
        channel = self.get_channel(self.config.status_channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel

        try:
            fetched = await self.fetch_channel(self.config.status_channel_id)
        except discord.Forbidden:
            self._log_channel_access_help()
            return None
        except discord.HTTPException:
            logger.exception("Could not fetch STATUS_CHANNEL_ID %s", self.config.status_channel_id)
            return None

        if isinstance(fetched, discord.TextChannel):
            return fetched

        logger.error(
            "STATUS_CHANNEL_ID %s is a %s, not a text channel",
            self.config.status_channel_id,
            type(fetched).__name__,
        )
        return None

    async def _update_status_message(self) -> None:
        channel = await self._get_status_channel()
        if channel is None:
            return

        embed = await self._gather_status_embed()
        message_id = self._load_status_message_id()

        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
                return
            except discord.NotFound:
                logger.warning("Status message %s not found; posting a new one", message_id)
            except discord.HTTPException:
                logger.exception("Failed to edit status message %s", message_id)

        message = await channel.send(embed=embed)
        self._save_status_message_id(message.id)

    def _load_status_message_id(self) -> int | None:
        if not self.config.state_file.exists():
            return None
        try:
            data: dict[str, Any] = json.loads(self.config.state_file.read_text())
            message_id = data.get("status_message_id")
            return int(message_id) if message_id else None
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def _save_status_message_id(self, message_id: int) -> None:
        self.config.state_file.write_text(
            json.dumps({"status_message_id": message_id}, indent=2) + "\n"
        )

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (%s)", self.user, self.user.id if self.user else "?")
        channel = await self._get_status_channel()
        if channel is not None:
            logger.info("Status channel ready: #%s (%s)", channel.name, channel.id)


def main() -> None:
    config = load_config()
    bot = GTNHBot(config)
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
