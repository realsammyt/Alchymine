"""Tests for the base MCPServer infrastructure."""

import pytest

from alchymine.mcp.base import MCPServer


# ─── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def server():
    """Create a fresh MCPServer with sample tools and resources."""
    srv = MCPServer(name="test-server", version="0.1.0")

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
    def add(a, b):
        return a + b

    @srv.tool(
        name="greet",
        description="Greet someone by name",
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    )
    def greet(name):
        return f"Hello, {name}!"

    @srv.resource(
        uri="test://info",
        name="Test Info",
        description="Test resource",
    )
    def info():
        return {"status": "ok"}

    return srv


# ─── Test: construction ─────────────────────────────────────────────────


def test_server_name_and_version(server):
    assert server.name == "test-server"
    assert server.version == "0.1.0"


def test_default_version():
    srv = MCPServer(name="default")
    assert srv.version == "1.0.0"


# ─── Test: tool registration and listing ─────────────────────────────────


def test_list_tools_returns_correct_count(server):
    tools = server.list_tools()
    assert len(tools) == 2


def test_list_tools_contains_correct_names(server):
    tools = server.list_tools()
    names = {t["name"] for t in tools}
    assert names == {"add", "greet"}


def test_list_tools_schema_format(server):
    tools = server.list_tools()
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert isinstance(tool["inputSchema"], dict)


def test_list_tools_description_populated(server):
    tools = server.list_tools()
    add_tool = next(t for t in tools if t["name"] == "add")
    assert add_tool["description"] == "Add two numbers"


# ─── Test: resource registration and listing ─────────────────────────────


def test_list_resources_returns_correct_count(server):
    resources = server.list_resources()
    assert len(resources) == 1


def test_list_resources_format(server):
    resources = server.list_resources()
    r = resources[0]
    assert r["uri"] == "test://info"
    assert r["name"] == "Test Info"
    assert r["description"] == "Test resource"
    assert r["mimeType"] == "application/json"


# ─── Test: tool calling ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_call_tool_add(server):
    result = await server.call_tool("add", {"a": 3, "b": 4})
    assert result == 7


@pytest.mark.asyncio
async def test_call_tool_greet(server):
    result = await server.call_tool("greet", {"name": "Alice"})
    assert result == "Hello, Alice!"


@pytest.mark.asyncio
async def test_call_tool_unknown_raises(server):
    with pytest.raises(ValueError, match="Unknown tool"):
        await server.call_tool("nonexistent", {})


@pytest.mark.asyncio
async def test_call_tool_missing_required_raises(server):
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("add", {"a": 1})


@pytest.mark.asyncio
async def test_call_tool_missing_all_required_raises(server):
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("greet", {})


# ─── Test: resource reading ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_read_resource(server):
    result = await server.read_resource("test://info")
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_read_resource_unknown_raises(server):
    with pytest.raises(ValueError, match="Unknown resource"):
        await server.read_resource("test://nonexistent")


# ─── Test: empty server ─────────────────────────────────────────────────


def test_empty_server_lists():
    srv = MCPServer(name="empty")
    assert srv.list_tools() == []
    assert srv.list_resources() == []


# ─── Test: decorator returns original function ──────────────────────────


def test_tool_decorator_preserves_function():
    srv = MCPServer(name="deco-test")

    @srv.tool(
        name="my_func",
        description="Test",
        input_schema={"type": "object", "properties": {}, "required": []},
    )
    def my_func():
        return 42

    # The decorated function should still be callable directly
    assert my_func() == 42


def test_resource_decorator_preserves_function():
    srv = MCPServer(name="deco-test")

    @srv.resource(uri="test://r", name="R", description="Test resource")
    def my_resource():
        return {"data": True}

    assert my_resource() == {"data": True}
