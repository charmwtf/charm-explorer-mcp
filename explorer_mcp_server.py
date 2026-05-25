#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import struct
import sys
import time
import traceback
from typing import Any

PIPE_NAME = os.environ.get("CHARM_EXPLORER_PIPE_NAME", r"\\.\pipe\charm_explorer_mcp")
SERVER_NAME = "charm-explorer"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = os.environ.get("CHARM_EXPLORER_MCP_PROTOCOL_VERSION", "2024-11-05")


def _merge_schema(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    merged_props = dict(base.get("properties", {}))
    merged_props.update(extra.get("properties", {}))
    merged["properties"] = merged_props

    required = list(base.get("required", []))
    for item in extra.get("required", []):
        if item not in required:
            required.append(item)
    if required:
        merged["required"] = required

    for key, value in extra.items():
        if key not in {"properties", "required"}:
            merged[key] = value
    return merged


def _target_schema(description: str = "Instance target.") -> dict[str, Any]:
    return {
        "type": "object",
        "description": description,
        "properties": {
            "path": {
                "type": "string",
                "description": "Instance path such as game/Workspace/Baseplate. Defaults to game when omitted.",
            },
            "address": {
                "type": ["integer", "string"],
                "description": "Absolute instance address as an integer or 0x-prefixed string.",
            },
        },
        "additionalProperties": True,
    }


TOOLS: list[dict[str, Any]] = [
    {
        "name": "status",
        "description": "Get explorer bridge status, including DataModel, Players, Workspace, and output directory details.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "scan_vtable_instances",
        "description": "Scan Roblox memory for live instances whose vtable pointer matches the supplied address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vtable": {
                    "type": ["integer", "string"],
                    "description": "Primary vtable address. You can also use vtable_address or address.",
                },
                "vtable_address": {
                    "type": ["integer", "string"],
                    "description": "Alternate field name for the vtable address.",
                },
                "address": {
                    "type": ["integer", "string"],
                    "description": "Alternate field name for the vtable address.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of matching instance addresses to return.",
                },
                "max_regions": {
                    "type": "integer",
                    "description": "Maximum committed memory regions to scan before stopping.",
                },
                "chunk_size": {
                    "type": "integer",
                    "description": "Chunk size, in bytes, for each ReadProcessMemory call.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_instance",
        "description": "Resolve an instance by path or address and return its basic metadata.",
        "inputSchema": _merge_schema(
            _target_schema(),
            {
                "properties": {
                    "include_children": {
                        "type": "boolean",
                        "description": "Include serialized direct children in the response.",
                    },
                },
                "additionalProperties": False,
            },
        ),
    },
    {
        "name": "list_children",
        "description": "List direct children of an instance resolved by path or address.",
        "inputSchema": _merge_schema(
            _target_schema(),
            {
                "properties": {
                    "max_children": {
                        "type": "integer",
                        "description": "Maximum number of direct children to return.",
                    },
                },
                "additionalProperties": False,
            },
        ),
    },
    {
        "name": "get_tree",
        "description": "Build a bounded subtree for an instance resolved by path or address.",
        "inputSchema": _merge_schema(
            _target_schema(),
            {
                "properties": {
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum recursion depth for the returned tree.",
                    },
                    "max_nodes": {
                        "type": "integer",
                        "description": "Maximum total nodes to serialize before truncating.",
                    },
                },
                "additionalProperties": False,
            },
        ),
    },
    {
        "name": "search_instances",
        "description": "Search a subtree for instances matching a name query and optional class filter.",
        "inputSchema": _merge_schema(
            _target_schema("Root instance for the search."),
            {
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Case-insensitive substring to match against instance names.",
                    },
                    "class_name": {
                        "type": "string",
                        "description": "Optional exact Roblox class name to filter by.",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum traversal depth under the root.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of matching instances to return.",
                    },
                },
                "additionalProperties": False,
            },
        ),
    },
    {
        "name": "inspect_render_assets",
        "description": "Inspect mesh, texture, and surface asset ids under an instance subtree.",
        "inputSchema": _merge_schema(
            _target_schema("Root instance for render asset inspection."),
            {
                "properties": {
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum traversal depth under the root.",
                    },
                    "max_nodes": {
                        "type": "integer",
                        "description": "Maximum total nodes to traverse before truncating.",
                    },
                    "include_containers": {
                        "type": "boolean",
                        "description": "Include non-render container instances in the response.",
                    },
                },
                "additionalProperties": False,
            },
        ),
    },
    {
        "name": "list_scripts",
        "description": "Enumerate Script, LocalScript, and ModuleScript instances under a root.",
        "inputSchema": _merge_schema(
            _target_schema("Root instance for script enumeration."),
            {
                "properties": {
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum number of script instances to return.",
                    },
                },
                "additionalProperties": False,
            },
        ),
    },
    {
        "name": "inspect_script",
        "description": "Inspect bytecode/decompiler candidates for a specific script instance.",
        "inputSchema": _merge_schema(
            _target_schema("Target script instance."),
            {
                "additionalProperties": False,
            },
        ),
    },
    {
        "name": "decompile_script",
        "description": "Decompile a specific script instance and optionally save output to a directory.",
        "inputSchema": _merge_schema(
            _target_schema("Target script instance."),
            {
                "properties": {
                    "output_dir": {
                        "type": "string",
                        "description": "Optional output directory for raw bytecode and decompiled Lua files.",
                    },
                },
                "additionalProperties": False,
            },
        ),
    },
    {
        "name": "search_script_source",
        "description": "Decompile scripts under a root and search their source, semantic refs, and raw strings for a query.",
        "inputSchema": _merge_schema(
            _target_schema("Root instance for script search."),
            {
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Required search string.",
                    },
                    "max_scripts": {
                        "type": "integer",
                        "description": "Maximum scripts to decompile and inspect.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum scripts with hits to return.",
                    },
                    "max_hits_per_script": {
                        "type": "integer",
                        "description": "Maximum hit records to keep per matching script.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Optional directory where decompiler artifacts should be written.",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        ),
    },
    {
        "name": "script_xrefs",
        "description": "Find scripts that reference a target script by searching for semantic, source, and raw-string xref terms.",
        "inputSchema": _merge_schema(
            _target_schema("Target script instance."),
            {
                "properties": {
                    "root_path": {
                        "type": "string",
                        "description": "Optional root path that bounds the xref scan. Defaults to game.",
                    },
                    "root_address": {
                        "type": ["integer", "string"],
                        "description": "Optional root address that bounds the xref scan.",
                    },
                    "max_scripts": {
                        "type": "integer",
                        "description": "Maximum scripts to decompile and inspect.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum referencing scripts to return.",
                    },
                    "max_hits_per_script": {
                        "type": "integer",
                        "description": "Maximum hit records to keep per matching script.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Optional directory where decompiler artifacts should be written.",
                    },
                },
                "additionalProperties": False,
            },
        ),
    },
    {
        "name": "bridge_request",
        "description": "Send a raw request to explorer_mcp_bridge.cpp. Prefer the typed tools above when possible.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Explorer bridge action name such as status, get_instance, or script_xrefs.",
                },
                "payload": {
                    "type": "object",
                    "description": "Additional request fields forwarded verbatim to the bridge.",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    },
]

ACTION_BY_TOOL = {
    "status": "status",
    "scan_vtable_instances": "scan_vtable_instances",
    "get_instance": "get_instance",
    "list_children": "list_children",
    "get_tree": "get_tree",
    "search_instances": "search_instances",
    "inspect_render_assets": "inspect_render_assets",
    "list_scripts": "list_scripts",
    "inspect_script": "inspect_script",
    "decompile_script": "decompile_script",
    "search_script_source": "search_script_source",
    "script_xrefs": "script_xrefs",
}


def read_exact(stream: Any, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = stream.read(size - len(chunks))
        if not chunk:
            raise EOFError("stream closed before the full payload was read")
        chunks.extend(chunk)
    return bytes(chunks)


def read_message(stream: Any) -> dict[str, Any] | None:
    headers: dict[str, str] = {}

    while True:
        line = stream.readline()
        if not line:
            return None

        if line in (b"\r\n", b"\n"):
            break

        decoded = line.decode("ascii", errors="replace").strip()
        if not decoded:
            continue

        name, separator, value = decoded.partition(":")
        if not separator:
            continue
        headers[name.strip().lower()] = value.strip()

    content_length_text = headers.get("content-length")
    if not content_length_text:
        raise ValueError("missing Content-Length header")

    content_length = int(content_length_text)
    if content_length < 0:
        raise ValueError("invalid Content-Length header")

    payload = read_exact(stream, content_length)
    return json.loads(payload.decode("utf-8"))


def write_message(stream: Any, message: dict[str, Any]) -> None:
    encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    stream.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii"))
    stream.write(encoded)
    stream.flush()


def pipe_read_exact(pipe: Any, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = pipe.read(size - len(chunks))
        if not chunk:
            raise OSError("explorer bridge closed the pipe early")
        chunks.extend(chunk)
    return bytes(chunks)


def forward_bridge_request(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            with open(PIPE_NAME, "r+b", buffering=0) as pipe:
                pipe.write(struct.pack("<I", len(encoded)))
                pipe.write(encoded)
                pipe.flush()
                response_size = struct.unpack("<I", pipe_read_exact(pipe, 4))[0]
                return json.loads(pipe_read_exact(pipe, response_size).decode("utf-8"))
        except (FileNotFoundError, OSError) as exc:
            last_error = exc
            if attempt == 2:
                break
            time.sleep(0.15)

    if last_error is not None:
        raise last_error
    raise RuntimeError("failed to forward explorer bridge request")


def make_text_result(payload: Any, is_error: bool = False) -> dict[str, Any]:
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, ensure_ascii=False)
    result: dict[str, Any] = {
        "content": [
            {
                "type": "text",
                "text": text,
            }
        ],
        "isError": is_error,
    }

    if isinstance(payload, dict):
        result["structuredContent"] = payload

    return result


def handle_tool_call(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    args = dict(arguments or {})

    try:
        if name == "bridge_request":
            action = args.get("action")
            if not isinstance(action, str) or not action:
                return make_text_result({"error": "bridge_request requires a non-empty action string."}, True)

            payload = dict(args.get("payload") or {})
            payload["action"] = action
        else:
            action = ACTION_BY_TOOL.get(name)
            if not action:
                return make_text_result({"error": f"Unknown tool: {name}"}, True)

            payload = args
            payload["action"] = action

        response = forward_bridge_request(payload)
    except Exception as exc:
        return make_text_result(
            {
                "error": str(exc),
                "tool": name,
                "pipe_name": PIPE_NAME,
            },
            True,
        )

    if not response.get("ok"):
        return make_text_result(response, True)

    return make_text_result(response.get("data", {}), False)


def make_response(message_id: Any, result: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "result": result,
    }


def make_error(message_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if data is not None:
        error["data"] = data

    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": error,
    }


def handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    message_id = request.get("id")
    params = request.get("params") or {}

    if not method:
        if message_id is None:
            return None
        return make_error(message_id, -32600, "Invalid request: missing method")

    if method == "initialize":
        return make_response(
            message_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        )

    if method == "ping":
        return make_response(message_id, {})

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return make_response(message_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments")
        if not isinstance(name, str) or not name:
            return make_error(message_id, -32602, "tools/call requires a non-empty tool name")
        if arguments is not None and not isinstance(arguments, dict):
            return make_error(message_id, -32602, "tools/call arguments must be an object")
        return make_response(message_id, handle_tool_call(name, arguments))

    if message_id is None:
        return None
    return make_error(message_id, -32601, f"Method not found: {method}")


def main() -> int:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    while True:
        request: dict[str, Any] | None = None
        try:
            request = read_message(stdin)
            if request is None:
                return 0

            response = handle_request(request)
            if response is not None:
                write_message(stdout, response)
        except EOFError:
            return 0
        except Exception as exc:
            message_id = None
            try:
                if isinstance(request, dict):
                    message_id = request.get("id")
            except Exception:
                message_id = None

            error_response = make_error(
                message_id,
                -32000,
                str(exc),
                {
                    "traceback": traceback.format_exc(limit=8),
                },
            )
            write_message(stdout, error_response)


if __name__ == "__main__":
    sys.exit(main())
