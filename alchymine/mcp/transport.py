"""JSON-RPC 2.0 HTTP transport layer for MCP servers.

Wraps each ``MCPServer`` instance in a FastAPI router with three
endpoints:

    POST /call    — invoke a tool (JSON-RPC 2.0 request/response)
    GET  /tools   — list available tools
    GET  /resources — list available resources

The ``make_mcp_router`` factory produces the router for a single
server; ``mount_all_mcp_routers`` mounts all five system routers
under ``/mcp/{system}``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .base import MCPServer

logger = logging.getLogger(__name__)

# ─── JSON-RPC 2.0 request / response models ────────────────────────────


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request envelope for tool calls."""

    jsonrpc: str = Field(default="2.0", pattern=r"^2\.0$")
    method: str = Field(..., description="Tool name to invoke")
    params: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    id: int | str | None = Field(default=None, description="Request identifier")


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 success response."""

    jsonrpc: str = "2.0"
    result: Any = None
    id: int | str | None = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error detail."""

    code: int
    message: str
    data: Any | None = None


class JSONRPCErrorResponse(BaseModel):
    """JSON-RPC 2.0 error response."""

    jsonrpc: str = "2.0"
    error: JSONRPCError
    id: int | str | None = None


# Standard JSON-RPC 2.0 error codes
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


# ─── Router factory ─────────────────────────────────────────────────────


def make_mcp_router(server: MCPServer, prefix: str = "") -> APIRouter:
    """Create a FastAPI router that exposes *server* over JSON-RPC 2.0.

    Parameters
    ----------
    server:
        The ``MCPServer`` instance whose tools/resources to expose.
    prefix:
        Optional path prefix forwarded to ``APIRouter(prefix=...)``.
    """
    router = APIRouter(prefix=prefix)

    @router.post("/call", response_model=JSONRPCResponse | JSONRPCErrorResponse)
    async def call_tool(request: JSONRPCRequest) -> JSONRPCResponse | JSONRPCErrorResponse:
        """Invoke a tool via JSON-RPC 2.0."""
        try:
            result = await server.call_tool(request.method, request.params)
            return JSONRPCResponse(result=result, id=request.id)
        except ValueError as exc:
            error_msg = str(exc)
            if "Unknown tool" in error_msg:
                code = METHOD_NOT_FOUND
            elif "Missing required argument" in error_msg:
                code = INVALID_PARAMS
            else:
                code = INVALID_PARAMS
            return JSONRPCErrorResponse(
                error=JSONRPCError(code=code, message=error_msg),
                id=request.id,
            )
        except Exception as exc:
            logger.exception("Internal error in tool call: %s", request.method)
            return JSONRPCErrorResponse(
                error=JSONRPCError(code=INTERNAL_ERROR, message=str(exc)),
                id=request.id,
            )

    @router.get("/tools")
    async def list_tools() -> list[dict[str, Any]]:
        """List all tools registered with this MCP server."""
        return server.list_tools()

    @router.get("/resources")
    async def list_resources() -> list[dict[str, Any]]:
        """List all resources registered with this MCP server."""
        return server.list_resources()

    return router


# ─── Convenience: mount all five system routers ─────────────────────────


def mount_all_mcp_routers(app_router: APIRouter) -> None:
    """Mount MCP transport routers for all five Alchymine systems.

    Each system is accessible at ``/mcp/{system}/call``,
    ``/mcp/{system}/tools``, and ``/mcp/{system}/resources``.

    Parameters
    ----------
    app_router:
        The parent router (or ``FastAPI`` app) to include the sub-routers on.
    """
    from .creative_server import server as creative_server
    from .healing_server import server as healing_server
    from .intelligence_server import server as intelligence_server
    from .perspective_server import server as perspective_server
    from .wealth_server import server as wealth_server

    systems: dict[str, MCPServer] = {
        "intelligence": intelligence_server,
        "healing": healing_server,
        "wealth": wealth_server,
        "creative": creative_server,
        "perspective": perspective_server,
    }

    for system_name, mcp_server in systems.items():
        router = make_mcp_router(mcp_server, prefix=f"/mcp/{system_name}")
        app_router.include_router(router, tags=[f"mcp-{system_name}"])
