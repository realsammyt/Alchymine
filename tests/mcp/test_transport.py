"""Tests for the MCP JSON-RPC 2.0 HTTP transport layer.

Covers:
- ``make_mcp_router`` factory with a standalone test MCPServer
- JSON-RPC 2.0 call semantics (success, method-not-found, invalid-params)
- ``/tools`` and ``/resources`` listing endpoints
- ``mount_all_mcp_routers`` with all five system servers
- Healing-specific ``list_skills`` and ``run_skill`` tools via transport
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient

from alchymine.mcp.base import MCPServer
from alchymine.mcp.transport import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    make_mcp_router,
    mount_all_mcp_routers,
)

# ─── Helpers ────────────────────────────────────────────────────────────


def _make_test_server() -> MCPServer:
    """Create a minimal MCPServer for transport tests."""
    srv = MCPServer(name="test-transport", version="0.1.0")

    @srv.tool(
        name="echo",
        description="Return the input message",
        input_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    )
    def echo(message: str) -> dict:
        return {"echo": message}

    @srv.tool(
        name="add",
        description="Add two numbers",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
    )
    def add(a: int | float, b: int | float) -> dict:
        return {"sum": a + b}

    @srv.resource(
        uri="test://info",
        name="Test Info",
        description="Test resource",
    )
    def info() -> dict:
        return {"status": "ok"}

    return srv


def _make_test_app(server: MCPServer | None = None) -> FastAPI:
    """Build a FastAPI app with the transport router mounted."""
    app = FastAPI()
    srv = server or _make_test_server()
    router = make_mcp_router(srv, prefix="/mcp/test")
    app.include_router(router)
    return app


@pytest.fixture
def test_app() -> FastAPI:
    return _make_test_app()


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# ─── POST /call — success ──────────────────────────────────────────────


async def test_call_echo(client: AsyncClient) -> None:
    resp = await client.post(
        "/mcp/test/call",
        json={"jsonrpc": "2.0", "method": "echo", "params": {"message": "hello"}, "id": 1},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["jsonrpc"] == "2.0"
    assert body["result"] == {"echo": "hello"}
    assert body["id"] == 1


async def test_call_add(client: AsyncClient) -> None:
    resp = await client.post(
        "/mcp/test/call",
        json={"jsonrpc": "2.0", "method": "add", "params": {"a": 3, "b": 4}, "id": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"] == {"sum": 7}
    assert body["id"] == 2


async def test_call_with_string_id(client: AsyncClient) -> None:
    resp = await client.post(
        "/mcp/test/call",
        json={
            "jsonrpc": "2.0",
            "method": "echo",
            "params": {"message": "test"},
            "id": "abc-123",
        },
    )
    body = resp.json()
    assert body["id"] == "abc-123"
    assert body["result"] == {"echo": "test"}


async def test_call_with_null_id(client: AsyncClient) -> None:
    resp = await client.post(
        "/mcp/test/call",
        json={"jsonrpc": "2.0", "method": "echo", "params": {"message": "notify"}},
    )
    body = resp.json()
    assert body["id"] is None
    assert body["result"] == {"echo": "notify"}


# ─── POST /call — errors ───────────────────────────────────────────────


async def test_call_unknown_method(client: AsyncClient) -> None:
    resp = await client.post(
        "/mcp/test/call",
        json={"jsonrpc": "2.0", "method": "nonexistent", "params": {}, "id": 10},
    )
    assert resp.status_code == 200  # JSON-RPC errors are 200 with error payload
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == METHOD_NOT_FOUND
    assert "Unknown tool" in body["error"]["message"]
    assert body["id"] == 10


async def test_call_missing_required_param(client: AsyncClient) -> None:
    resp = await client.post(
        "/mcp/test/call",
        json={"jsonrpc": "2.0", "method": "add", "params": {"a": 1}, "id": 11},
    )
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == INVALID_PARAMS
    assert "Missing required argument" in body["error"]["message"]


async def test_call_empty_params(client: AsyncClient) -> None:
    resp = await client.post(
        "/mcp/test/call",
        json={"jsonrpc": "2.0", "method": "echo", "params": {}, "id": 12},
    )
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == INVALID_PARAMS


# ─── POST /call — internal error ───────────────────────────────────────


async def test_call_internal_error() -> None:
    """A tool that raises a non-ValueError should produce INTERNAL_ERROR."""
    srv = MCPServer(name="err-test")

    @srv.tool(
        name="boom",
        description="Always fails",
        input_schema={"type": "object", "properties": {}, "required": []},
    )
    def boom() -> None:
        raise RuntimeError("kaboom")

    app = _make_test_app(srv)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/mcp/test/call",
            json={"jsonrpc": "2.0", "method": "boom", "params": {}, "id": 99},
        )
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == INTERNAL_ERROR
    assert "kaboom" in body["error"]["message"]


# ─── GET /tools ─────────────────────────────────────────────────────────


async def test_list_tools(client: AsyncClient) -> None:
    resp = await client.get("/mcp/test/tools")
    assert resp.status_code == 200
    tools = resp.json()
    names = {t["name"] for t in tools}
    assert names == {"echo", "add"}
    for t in tools:
        assert "description" in t
        assert "inputSchema" in t


# ─── GET /resources ─────────────────────────────────────────────────────


async def test_list_resources(client: AsyncClient) -> None:
    resp = await client.get("/mcp/test/resources")
    assert resp.status_code == 200
    resources = resp.json()
    assert len(resources) == 1
    assert resources[0]["uri"] == "test://info"
    assert resources[0]["name"] == "Test Info"


# ─── mount_all_mcp_routers — smoke test ─────────────────────────────────


async def test_mount_all_systems_tools() -> None:
    """All five system routers should be reachable via /mcp/{system}/tools."""
    app = FastAPI()
    parent = APIRouter()
    mount_all_mcp_routers(parent)
    app.include_router(parent)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for system in ("intelligence", "healing", "wealth", "creative", "perspective"):
            resp = await client.get(f"/mcp/{system}/tools")
            assert resp.status_code == 200, f"/mcp/{system}/tools failed"
            tools = resp.json()
            assert isinstance(tools, list)
            assert len(tools) > 0, f"/mcp/{system}/tools returned no tools"


async def test_mount_all_systems_resources() -> None:
    """All five system routers should expose their resources."""
    app = FastAPI()
    parent = APIRouter()
    mount_all_mcp_routers(parent)
    app.include_router(parent)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for system in ("intelligence", "healing", "wealth", "creative", "perspective"):
            resp = await client.get(f"/mcp/{system}/resources")
            assert resp.status_code == 200, f"/mcp/{system}/resources failed"


async def test_mount_healing_call_detect_crisis() -> None:
    """Verify a real tool call works through the transport layer."""
    app = FastAPI()
    parent = APIRouter()
    mount_all_mcp_routers(parent)
    app.include_router(parent)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/mcp/healing/call",
            json={
                "jsonrpc": "2.0",
                "method": "detect_crisis",
                "params": {"text": "I had a great day"},
                "id": 1,
            },
        )
    body = resp.json()
    assert body["jsonrpc"] == "2.0"
    assert body["result"] is None  # no crisis
    assert body["id"] == 1


# ─── Healing skill tools via transport ──────────────────────────────────


async def test_healing_list_skills_via_transport() -> None:
    """list_skills should return skills through the JSON-RPC transport."""
    app = FastAPI()
    parent = APIRouter()
    mount_all_mcp_routers(parent)
    app.include_router(parent)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/mcp/healing/call",
            json={
                "jsonrpc": "2.0",
                "method": "list_skills",
                "params": {},
                "id": 1,
            },
        )
    body = resp.json()
    assert "result" in body
    skills = body["result"]
    assert isinstance(skills, list)
    assert len(skills) >= 15  # 15 seed skills
    for s in skills:
        assert "name" in s
        assert "title" in s
        assert "modality" in s
        assert "evidence_rating" in s
        assert "duration_minutes" in s


async def test_healing_list_skills_by_modality_via_transport() -> None:
    """list_skills with modality filter should return only matching skills."""
    app = FastAPI()
    parent = APIRouter()
    mount_all_mcp_routers(parent)
    app.include_router(parent)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/mcp/healing/call",
            json={
                "jsonrpc": "2.0",
                "method": "list_skills",
                "params": {"modality": "breathwork"},
                "id": 2,
            },
        )
    body = resp.json()
    skills = body["result"]
    assert isinstance(skills, list)
    assert len(skills) >= 1
    for s in skills:
        assert s["modality"] == "breathwork"


async def test_healing_run_skill_via_transport() -> None:
    """run_skill should return the full practice card through transport."""
    app = FastAPI()
    parent = APIRouter()
    mount_all_mcp_routers(parent)
    app.include_router(parent)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/mcp/healing/call",
            json={
                "jsonrpc": "2.0",
                "method": "run_skill",
                "params": {"name": "breathwork-box-breathing"},
                "id": 3,
            },
        )
    body = resp.json()
    assert "result" in body
    skill = body["result"]
    assert skill["name"] == "breathwork-box-breathing"
    assert skill["title"] == "Box Breathing (4-4-4-4)"
    assert skill["modality"] == "breathwork"
    assert isinstance(skill["steps"], list)
    assert len(skill["steps"]) > 0
    assert skill["evidence_rating"] == "B"
    assert isinstance(skill["contraindications"], list)
    assert skill["duration_minutes"] == 6


async def test_healing_run_skill_not_found_via_transport() -> None:
    """run_skill with unknown name should return JSON-RPC error."""
    app = FastAPI()
    parent = APIRouter()
    mount_all_mcp_routers(parent)
    app.include_router(parent)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/mcp/healing/call",
            json={
                "jsonrpc": "2.0",
                "method": "run_skill",
                "params": {"name": "nonexistent-skill"},
                "id": 4,
            },
        )
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == INVALID_PARAMS
    assert "Skill not found" in body["error"]["message"]


async def test_healing_tools_include_skill_tools() -> None:
    """The healing server /tools endpoint should include list_skills and run_skill."""
    app = FastAPI()
    parent = APIRouter()
    mount_all_mcp_routers(parent)
    app.include_router(parent)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/mcp/healing/tools")
    tools = resp.json()
    names = {t["name"] for t in tools}
    assert "list_skills" in names
    assert "run_skill" in names
    # Original tools should still be present
    assert "detect_crisis" in names
    assert "match_modalities" in names
    assert "get_breathwork" in names
