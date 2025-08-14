import asyncio
import json
import os
import logging
from typing import List

import aiohttp
import yaml
from dotenv import load_dotenv

from service_client import KeyServiceClient, NodeConfig, NodeStatus
from base_poller import BasePoller

load_dotenv()

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

POST_RESULTS = os.environ.get("POST_RESULTS", "false").lower() == "true"
RESULTS_URL = os.environ.get("RESULTS_URL", "")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
CONFIG_FILE = os.environ.get("CONFIG_FILE", "config.yaml")


def load_config(path: str) -> List[NodeConfig]:
    logger.info("Loading configuration from %s", path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    names = data.get("names", [])
    consumers = data.get("consumers", [])
    urls = data.get("urls", {})
    paths = data.get("paths", {})

    nodes: List[NodeConfig] = []

    if paths:
        for src_name, consumer_map in paths.items():
            url = urls.get(src_name, "")
            for src_consumer, dests in consumer_map.items():
                for dest_kme, dest_consumer in dests:
                    sae_id = f"{src_name}-{dest_consumer}"
                    nodes.append(
                        NodeConfig(
                            name=src_name,
                            base_url=url,
                            kme=dest_kme,
                            consumer=dest_consumer,
                            sae_id=sae_id,
                        )
                    )
    else:
        for name in names:
            url = urls.get(name, "")
            for consumer in consumers:
                nodes.append(
                    NodeConfig(name=name, base_url=url, kme=name, consumer=consumer)
                )

    logger.info("Loaded %d node configurations", len(nodes))
    return nodes


async def monitor(nodes: List[NodeConfig]):
    logger.info("Monitor started for %d nodes", len(nodes))
    async with aiohttp.ClientSession() as session:
        client: BasePoller[NodeStatus] = KeyServiceClient(nodes, session)
        while True:
            statuses: List[NodeStatus] = await client.poll()
            unified = {
                "nodes": [
                    {
                        "name": s.name,
                        "status": s.status,
                        "stored_key_count": s.stored_key_count,
                        "current_key_rate": s.current_key_rate,
                    }
                    for s in statuses
                ]
            }
            if POST_RESULTS and RESULTS_URL:
                headers = {"X-Auth-Token": f"Bearer {AUTH_TOKEN}"} if AUTH_TOKEN else {}
                logger.debug("POST %s headers=%s", RESULTS_URL, list(headers.keys()))
                try:
                    async with session.post(RESULTS_URL, json=unified, headers=headers) as resp:
                        resp.raise_for_status()
                except Exception as exc:
                    print(f"Error posting results: {exc}")
            logger.debug(json.dumps(unified, indent=2))
            await asyncio.sleep(POLL_INTERVAL)


def main() -> None:
    logger.info("Starting MonDash agent")
    logger.debug("Poll interval set to %d seconds", POLL_INTERVAL)
    if POST_RESULTS and RESULTS_URL:
        logger.debug("Results will be posted to %s", RESULTS_URL)
    nodes = load_config(CONFIG_FILE)
    if not nodes:
        raise SystemExit("No nodes configured")
    asyncio.run(monitor(nodes))


if __name__ == "__main__":
    main()
