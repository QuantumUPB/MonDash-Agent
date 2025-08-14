from dataclasses import dataclass
from typing import List
import asyncio
import os
import json
import logging

import aiohttp
import yaml
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class NodeConfig:
    """Configuration for a monitored node."""

    name: str
    base_url: str
    kme: str
    consumer: str
    sae_id: str = ""

    def __post_init__(self) -> None:
        """Set SAE identifier based on node name and consumer if missing."""
        if not self.sae_id:
            self.sae_id = f"{self.name}-{self.consumer}"


@dataclass
class NodeStatus:
    name: str
    status: str
    stored_key_count: int
    current_key_rate: float


from base_poller import BasePoller


class KeyServiceClient(BasePoller[NodeStatus]):
    """Client for retrieving node status information."""

    def __init__(
        self,
        nodes: List[NodeConfig],
        session: aiohttp.ClientSession,
        config_path: str = "config.yaml",
    ):
        self.nodes = nodes
        self.session = session
        # Load KME configuration to validate endpoint combinations
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            data = {}
        self.paths = data.get("paths", {})

    async def _get_json(self, url: str) -> dict:
        logger.debug("GET %s", url)
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _curl_json(self, node: NodeConfig) -> dict:
        """Call the key service using curl with TLS parameters from env vars."""
        cert_path = os.environ.get("CERT_PATH", "")
        pem_password = os.environ.get("PEM_PASSWORD", "")
        key_path = os.environ.get("KEY_PATH", "")
        cacert_path = os.environ.get("CACERT_PATH", "")
        ipport = os.environ.get("IPPORT", "")
        scheme = urlparse(node.base_url).scheme or "https"
        url = f"{scheme}://{ipport}/{node.kme}/{node.consumer}/api/v1/keys/{node.sae_id}/status"

        cmd = ["curl", "-Ss"]

        if cert_path:
            cert_arg = cert_path
            if pem_password:
                cert_arg = f"{cert_path}:{pem_password}"
            cmd.extend(["--cert", cert_arg])
        if key_path:
            cmd.extend(["--key", key_path])
        if cacert_path:
            cmd.extend(["--cacert", cacert_path])

        cmd.extend(["-k", url])
        logger.debug(cmd)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode().strip())
        response_text = stdout.decode() or "{}"
        logger.debug("curl output: %s", response_text.strip())
        return json.loads(response_text)

    @staticmethod
    def _extract_stats(payload: dict) -> tuple[int, float]:
        """Return stored key count and generation rate from service payload."""
        stored = 0
        rate = 0.0
        if isinstance(payload, dict):
            stored = int(payload.get("stored_key_count", 0))
            rate = float(payload.get("current_key_rate", 0.0))
        return stored, rate

    def _is_valid(self, node: NodeConfig) -> bool:
        """Return True if the node/consumer combination is allowed."""
        if not self.paths:
            return True

        consumer_map = self.paths.get(node.name)
        if consumer_map is None:
            return False
        dests = consumer_map.get(node.consumer)
        if dests is None:
            return False

        return [node.kme, node.consumer] in dests

    async def fetch_status(self, node: NodeConfig) -> NodeStatus:
        try:
            status_data = await self._get_json(
                f"{node.base_url}/nodes/{node.name}/status"
            )
            node_status = status_data.get("status", "down")
        except Exception:
            return NodeStatus(node.name, "down", 0, 0.0)

        stored = 0
        rate = 0.0
        if self._is_valid(node):
            try:
                info = await self._curl_json(node)
                # Extract statistics from the returned payload.  The endpoint
                # returns a JSON object similar to::
                # {
                #   "current_key_rate": 3.5,
                #   "stored_key_count": 42,
                #   ...
                # }
                stored, rate = self._extract_stats(info)
            except Exception as exc:
                logger.warning(
                    "Failed to fetch key service status for %s: %s",
                    node.sae_id,
                    exc,
                )
                stored = 0
                rate = 0.0

        return NodeStatus(node.name, node_status, stored, rate)

    async def _fetch_node_statuses(self) -> dict[tuple[str, str], str]:
        """Fetch the /status endpoint for each unique node once."""
        tasks: dict[tuple[str, str], asyncio.Task] = {}
        for node in self.nodes:
            key = (node.base_url, node.name)
            if key in tasks:
                continue
            url = f"{node.base_url}/nodes/{node.name}/status"
            tasks[key] = asyncio.create_task(self._get_json(url))

        status_map: dict[tuple[str, str], str] = {}
        for key, task in tasks.items():
            try:
                data = await task
                status_map[key] = data.get("status", "down")
            except Exception:
                status_map[key] = "down"

        return status_map

    async def _build_status(
        self, node: NodeConfig, status_map: dict[tuple[str, str], str]
    ) -> NodeStatus:
        node_status = status_map.get((node.base_url, node.name), "down")

        stored = 0
        rate = 0.0
        if self._is_valid(node):
            try:
                info = await self._curl_json(node)
                stored, rate = self._extract_stats(info)
            except Exception as exc:
                logger.warning(
                    "Failed to fetch key service status for %s: %s",
                    node.sae_id,
                    exc,
                )
                stored = 0
                rate = 0.0

        return NodeStatus(node.name, node_status, stored, rate)

    async def poll(self) -> List[NodeStatus]:
        status_map = await self._fetch_node_statuses()
        results = await asyncio.gather(
            *(self._build_status(n, status_map) for n in self.nodes),
            return_exceptions=False,
        )
        return list(results)
