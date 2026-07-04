"""Docker Compose wrappers for the GTNH Minecraft server."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ContainerState(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ComposeStatus:
    state: ContainerState
    service: str
    status_text: str | None = None


class DockerControl:
    def __init__(self, compose_dir: Path, service: str) -> None:
        self.compose_dir = compose_dir
        self.service = service

    async def _run(self, *args: str, timeout: float = 60.0) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
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
            raise

        out = stdout.decode().strip()
        err = stderr.decode().strip()
        if proc.returncode != 0:
            logger.warning("Command failed (%s): %s", proc.returncode, err or out)
        return proc.returncode, out, err

    async def get_status(self) -> ComposeStatus:
        code, out, _ = await self._run(
            "docker",
            "compose",
            "ps",
            "--format",
            "json",
            self.service,
        )
        if code != 0 or not out:
            return ComposeStatus(ContainerState.STOPPED, self.service)

        # docker compose may emit one JSON object per line
        lines = [line for line in out.splitlines() if line.strip()]
        if not lines:
            return ComposeStatus(ContainerState.STOPPED, self.service)

        try:
            data = json.loads(lines[0])
        except json.JSONDecodeError:
            return ComposeStatus(ContainerState.UNKNOWN, self.service, out)

        state_raw = (data.get("State") or data.get("Status") or "").lower()
        if "running" in state_raw:
            return ComposeStatus(ContainerState.RUNNING, self.service, data.get("Status"))
        if "starting" in state_raw or "created" in state_raw:
            return ComposeStatus(ContainerState.STARTING, self.service, data.get("Status"))
        if "exited" in state_raw or "stopped" in state_raw or "dead" in state_raw:
            return ComposeStatus(ContainerState.STOPPED, self.service, data.get("Status"))

        return ComposeStatus(ContainerState.UNKNOWN, self.service, data.get("Status"))

    async def start(self) -> tuple[bool, str]:
        code, out, err = await self._run(
            "docker",
            "compose",
            "up",
            "-d",
            self.service,
            timeout=120.0,
        )
        message = out or err or "docker compose up -d"
        return code == 0, message

    async def stop(self) -> tuple[bool, str]:
        code, out, err = await self._run(
            "docker",
            "compose",
            "stop",
            self.service,
            timeout=120.0,
        )
        message = out or err or "docker compose stop"
        return code == 0, message
