import os, sys; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import aiohttp
from aiohttp import web
import pytest

from service_client import KeyServiceClient, NodeConfig
from base_poller import BasePoller
from mock import stub_curl_json


def test_keyserviceclient_inherits_basepoller():
    assert issubclass(KeyServiceClient, BasePoller)


@pytest.mark.asyncio
async def test_fetch_status(monkeypatch, aiohttp_server):
    async def status_handler(request):
        return web.json_response({"status": "up"})

    app = web.Application()
    app.router.add_get("/nodes/campus/status", status_handler)
    server = await aiohttp_server(app)

    node = NodeConfig(
        name="campus",
        base_url=str(server.make_url("")),
        kme="precisA",
        consumer="fileTransfer1",
    )

    async with aiohttp.ClientSession() as session:
        client = KeyServiceClient([node], session)
        monkeypatch.setattr(KeyServiceClient, "_curl_json", stub_curl_json)
        status = await client.fetch_status(node)

    assert status.name == "campus"
    assert status.status == "up"
    assert status.stored_key_count == 42
    assert status.current_key_rate == 3.5


@pytest.mark.asyncio
async def test_poll_deduplicates_status_requests(monkeypatch, aiohttp_server):
    call_count = 0

    async def status_handler(request):
        nonlocal call_count
        call_count += 1
        return web.json_response({"status": "up"})

    app = web.Application()
    app.router.add_get("/nodes/campus/status", status_handler)
    server = await aiohttp_server(app)

    base_url = str(server.make_url(""))
    nodes = [
        NodeConfig(name="campus", base_url=base_url, kme="kme1", consumer="c1"),
        NodeConfig(name="campus", base_url=base_url, kme="kme2", consumer="c2"),
    ]

    async with aiohttp.ClientSession() as session:
        client = KeyServiceClient(nodes, session)
        monkeypatch.setattr(KeyServiceClient, "_curl_json", stub_curl_json)
        await client.poll()

    assert call_count == 1
