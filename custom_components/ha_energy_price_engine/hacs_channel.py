"""User-approved PE-only beta channel repair through supported HACS WebSocket API."""

import asyncio
import ipaddress
import re

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.http import current_request

REPOSITORY = "NicolaiTandrup/HA-Energy-Price-Engine"
SEMANTIC = re.compile(r"v?\d+\.\d+\.\d+(?:-[A-Za-z]+[.\d]*)?$")


async def enable_beta_channel(hass):
    """Never install, download, change global settings or forward credentials remotely."""
    request = current_request.get()
    if request is None or not (user := request.get("hass_user")) or not user.is_admin:
        raise ValueError("An authenticated administrator request is required")
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer ") or request.transport is None:
        raise ValueError("Use Configure while signed in as an administrator")
    # The actual local listening socket, never Host/forwarded headers or a URL
    # supplied by a user. The existing token lives only for this local connection.
    address = request.transport.get_extra_info("sockname")
    if not isinstance(address, tuple) or len(address) < 2:
        raise ValueError("Local Home Assistant socket unavailable")
    host = ipaddress.ip_address(address[0])
    if host.is_unspecified or host.is_multicast or not (host.is_loopback or host.is_private):
        raise ValueError("A local Home Assistant socket is required")
    scheme = "wss" if request.transport.get_extra_info("ssl_object") else "ws"
    literal = f"[{host}]" if host.version == 6 else str(host)
    url = f"{scheme}://{literal}:{int(address[1])}/api/websocket"
    try:
        async with asyncio.timeout(30):
            session = async_get_clientsession(hass)
            async with session.ws_connect(url, ssl=False) as ws:
                if (await ws.receive_json()).get("type") != "auth_required":
                    raise ValueError("Unexpected local authentication response")
                await ws.send_json(
                    {"type": "auth", "access_token": authorization.removeprefix("Bearer ")}
                )
                if (await ws.receive_json()).get("type") != "auth_ok":
                    raise ValueError("Local authentication failed")
                counter = 0

                async def call(command, **data):
                    nonlocal counter
                    counter += 1
                    await ws.send_json({"id": counter, "type": command, **data})
                    reply = await ws.receive_json()
                    if reply.get("id") != counter or not reply.get("success"):
                        raise ValueError("HACS could not complete this channel operation")
                    return reply.get("result")

                repos = await call("hacs/repositories/list", categories=["integration"])
                matches = [
                    repo
                    for repo in repos
                    if repo.get("full_name", "").casefold() == REPOSITORY.casefold()
                ]
                if len(matches) != 1:
                    raise ValueError("Register Energy Price Engine in HACS first")
                repo_id = str(matches[0]["id"])
                before = await call("hacs/repository/info", repository_id=repo_id)
                if before.get("full_name", "").casefold() != REPOSITORY.casefold():
                    raise ValueError("HACS repository identity mismatch")
                if not before.get("beta"):
                    await call("hacs/repository/beta", repository=repo_id, show_beta=True)
                after = await call("hacs/repository/info", repository_id=repo_id)
                latest = after.get("available_version", "")
                if not after.get("beta") or not SEMANTIC.fullmatch(latest):
                    raise ValueError(
                        "HACS has not discovered a published semantic release; refresh its repository information"
                    )
                return latest
    except (aiohttp.ClientError, TimeoutError, KeyError, TypeError) as err:
        raise ValueError(
            "HACS unavailable; open HACS, enable Show beta versions for PE and refresh information"
        ) from err
