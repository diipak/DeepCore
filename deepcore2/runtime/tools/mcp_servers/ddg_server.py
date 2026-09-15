#!/usr/bin/env python3
"""
DuckDuckGo MCP Server for DeepCore.

Implements a standard Model Context Protocol (MCP) JSON-RPC 2.0 stdio server
exposing live DuckDuckGo web search capabilities without requiring API keys.
Employs `ddgs` with browser TLS fingerprint impersonation (primp) to prevent
anti-bot challenges.
"""

import json
import logging
import sys
from typing import Any, Dict, List

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
logger = logging.getLogger("duckduckgo-mcp")


def _execute_search(query: str, max_results: int = 5) -> str:
    """Execute DuckDuckGo search using ddgs with browser impersonation."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return "Error: Neither 'ddgs' nor 'duckduckgo_search' is installed in the python environment."

    try:
        max_n = max(1, min(int(max_results), 10))
        results = list(DDGS().text(query, max_results=max_n))
        if not results:
            return f"No search results found for query: '{query}'."

        formatted_blocks: List[str] = []
        for idx, item in enumerate(results, 1):
            title = item.get("title", "No title")
            link = item.get("href", "")
            body = item.get("body", "")
            formatted_blocks.append(f"[{idx}] {title}\nURL: {link}\n{body}")

        return "\n\n".join(formatted_blocks)
    except Exception as exc:
        return f"DuckDuckGo search error: {exc}"


def main() -> None:
    """Main JSON-RPC stdio loop."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = request.get("method")
        req_id = request.get("id")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "deepcore-duckduckgo-mcp",
                        "version": "1.0.0",
                    },
                },
            }
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            # Handshake notification, no response expected
            continue

        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "duckduckgo_web_search",
                            "description": (
                                "Perform live internet web search using DuckDuckGo. "
                                "Zero API key required. Use to look up current events, "
                                "documentation, news, and general web information."
                            ),
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The search query to look up on the web.",
                                    },
                                    "max_results": {
                                        "type": "integer",
                                        "description": "Maximum number of search result items (1 to 10). Default 5.",
                                        "default": 5,
                                    },
                                },
                                "required": ["query"],
                            },
                        }
                    ]
                },
            }
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "duckduckgo_web_search":
                q = arguments.get("query", "")
                max_r = arguments.get("max_results", 5)
                output_text = _execute_search(query=q, max_results=max_r)

                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": output_text,
                            }
                        ]
                    },
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool '{tool_name}' not found.",
                    },
                }

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        elif method == "ping":
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": {}}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
