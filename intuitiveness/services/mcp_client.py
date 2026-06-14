"""
MCP Client - HTTP Transport
============================

Generic Model Context Protocol client for Streamable HTTP transport.
Implements JSON-RPC 2.0 over HTTP as per MCP specification.

Feature: 008-datagouv-mcp
Reference: https://modelcontextprotocol.io/docs/concepts/transports
"""

import requests
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


# MCP Protocol Version
MCP_PROTOCOL_VERSION = "2025-06-18"


@dataclass
class MCPTool:
    """Represents an MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResponse:
    """Represents an MCP response."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[int] = None


class MCPClient:
    """
    MCP Client for HTTP Streamable transport.

    Handles:
    - Session initialization
    - Tool listing
    - Tool invocation

    Example:
        client = MCPClient("https://mcp.data.gouv.fr/mcp")
        client.initialize()
        tools = client.list_tools()
        result = client.call_tool("search_datasets", {"q": "éducation"})
    """

    def __init__(self, endpoint: str, timeout: int = 30):
        """
        Initialize MCP client.

        Args:
            endpoint: MCP server endpoint URL
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint.rstrip('/')
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self.request_id: int = 0
        self._tools: Dict[str, MCPTool] = {}
        self._initialized = False

    def _get_headers(self) -> Dict[str, str]:
        """Get required headers for MCP requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    def _send_request(self, method: str, params: Optional[Dict] = None) -> MCPResponse:
        """
        Send a JSON-RPC request to the MCP server.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            MCPResponse with result or error
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params:
            payload["params"] = params

        try:
            # Use data= with explicit UTF-8 encoding to preserve
            # non-ASCII characters (French accents) in MCP queries
            import json as _json
            encoded_body = _json.dumps(payload, ensure_ascii=False).encode("utf-8")

            response = requests.post(
                self.endpoint,
                headers=self._get_headers(),
                data=encoded_body,
                timeout=self.timeout
            )
            response.encoding = "utf-8"

            # Check for session ID in response
            if "Mcp-Session-Id" in response.headers:
                self.session_id = response.headers["Mcp-Session-Id"]

            # Handle SSE response
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                # Parse SSE - look for data: lines
                data = self._parse_sse(response.text)
            else:
                # Regular JSON response
                data = response.json()

            # Check for JSON-RPC error
            if "error" in data:
                return MCPResponse(
                    success=False,
                    error=data["error"].get("message", "Unknown error"),
                    error_code=data["error"].get("code")
                )

            return MCPResponse(success=True, data=data.get("result"))

        except requests.exceptions.Timeout:
            return MCPResponse(success=False, error="Request timeout")
        except requests.exceptions.RequestException as e:
            return MCPResponse(success=False, error=f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            return MCPResponse(success=False, error=f"Invalid JSON response: {str(e)}")

    def _parse_sse(self, text: str) -> Dict:
        """Parse Server-Sent Events response."""
        for line in text.split('\n'):
            if line.startswith('data:'):
                data_str = line[5:].strip()
                if data_str:
                    return json.loads(data_str)
        return {}

    def initialize(self) -> MCPResponse:
        """
        Initialize the MCP session.

        Sends the initialize request to establish capabilities.

        Returns:
            MCPResponse with server capabilities
        """
        params = {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "data-redesign-method",
                "version": "1.0.0"
            }
        }

        response = self._send_request("initialize", params)

        if response.success:
            self._initialized = True
            # Send initialized notification
            self._send_notification("notifications/initialized")

        return response

    def _send_notification(self, method: str, params: Optional[Dict] = None):
        """Send a notification (no response expected)."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            payload["params"] = params

        try:
            requests.post(
                self.endpoint,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout
            )
        except:
            pass  # Notifications don't require response handling

    def list_tools(self) -> List[MCPTool]:
        """
        List available tools from the MCP server.

        Returns:
            List of MCPTool objects
        """
        if not self._initialized:
            init_response = self.initialize()
            if not init_response.success:
                return []

        response = self._send_request("tools/list")

        if not response.success:
            return []

        tools = []
        for tool_data in response.data.get("tools", []):
            tool = MCPTool(
                name=tool_data.get("name", ""),
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {})
            )
            self._tools[tool.name] = tool
            tools.append(tool)

        return tools

    def call_tool(self, name: str, arguments: Optional[Dict] = None) -> MCPResponse:
        """
        Call an MCP tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            MCPResponse with tool result
        """
        if not self._initialized:
            init_response = self.initialize()
            if not init_response.success:
                return init_response

        params = {"name": name}
        if arguments:
            params["arguments"] = arguments

        return self._send_request("tools/call", params)

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a tool definition by name."""
        if not self._tools:
            self.list_tools()
        return self._tools.get(name)

    def close(self):
        """Close the MCP session."""
        if self.session_id:
            try:
                requests.delete(
                    self.endpoint,
                    headers=self._get_headers(),
                    timeout=5
                )
            except:
                pass
            self.session_id = None
            self._initialized = False

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# =============================================================================
# Exports
# =============================================================================

__all__ = ['MCPClient', 'MCPTool', 'MCPResponse', 'MCP_PROTOCOL_VERSION']
