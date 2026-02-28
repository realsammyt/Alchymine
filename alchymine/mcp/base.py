"""Base MCP server infrastructure for Alchymine.

Provides a lightweight MCP-compatible server that exposes
engine capabilities as tools with JSON Schema validation.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definition of a single MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any]


@dataclass
class ResourceDefinition:
    """Definition of a single MCP resource."""

    uri: str
    name: str
    description: str
    mime_type: str = "application/json"
    handler: Callable[..., Any] | None = None


class MCPServer:
    """Base MCP server that manages tools and resources.

    Each Alchymine system (Intelligence, Healing, Wealth, Creative,
    Perspective) creates its own MCPServer instance and registers
    tools via the ``@server.tool(...)`` decorator.
    """

    def __init__(self, name: str, version: str = "1.0.0") -> None:
        self.name = name
        self.version = version
        self._tools: dict[str, ToolDefinition] = {}
        self._resources: dict[str, ResourceDefinition] = {}

    def tool(self, name: str, description: str, input_schema: dict[str, Any]) -> Callable[..., Any]:
        """Decorator to register a tool handler."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._tools[name] = ToolDefinition(name, description, input_schema, func)
            return func

        return decorator

    def resource(self, uri: str, name: str, description: str) -> Callable[..., Any]:
        """Decorator to register a resource handler."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._resources[uri] = ResourceDefinition(uri, name, description, handler=func)
            return func

        return decorator

    def list_tools(self) -> list[dict[str, Any]]:
        """Return all registered tools as MCP-compatible dicts."""
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
            for t in self._tools.values()
        ]

    def list_resources(self) -> list[dict[str, Any]]:
        """Return all registered resources as MCP-compatible dicts."""
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "mimeType": r.mime_type,
            }
            for r in self._resources.values()
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a registered tool by name with the given arguments.

        Raises
        ------
        ValueError
            If the tool name is unknown or a required argument is missing.
        """
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        # Validate required fields from schema
        required = tool.input_schema.get("required", [])
        for req in required:
            if req not in arguments:
                raise ValueError(f"Missing required argument: {req}")
        result = tool.handler(**arguments)
        return result

    async def read_resource(self, uri: str) -> Any:
        """Read a registered resource by URI.

        Raises
        ------
        ValueError
            If the resource URI is unknown.
        """
        resource = self._resources.get(uri)
        if not resource:
            raise ValueError(f"Unknown resource: {uri}")
        if resource.handler:
            return resource.handler()
        return None
