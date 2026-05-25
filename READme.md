# Charm Explorer MCP

[![MCP](https://img.shields.io/badge/MCP-compatible-blue)](https://modelcontextprotocol.io/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)](#requirements)

A [Model Context Protocol](https://modelcontextprotocol.io/) server that bridges AI assistants to a live Roblox process via a native explorer bridge (`explorer_mcp_bridge.cpp`). It exposes typed tools for inspecting the DataModel, scanning memory, walking the instance tree, enumerating render assets, and decompiling scripts — all over a named pipe.

> ⚠️ **Research / educational use only.** This server is designed to interact with a Roblox process through a custom native bridge. You are responsible for complying with [Roblox's Terms of Service](https://en.help.roblox.com/hc/en-us/articles/115004647846) and any applicable laws.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Client Setup](#client-setup)
  - [Claude Desktop](#claude-desktop)
  - [Claude Code](#claude-code)
  - [Codex CLI](#codex-cli)
  - [VS Code (Continue / Cline / Roo)](#vs-code-continue--cline--roo)
  - [Cursor](#cursor)
  - [Zed](#zed)
- [Tools](#tools)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

- 🔍 **Live instance inspection** — resolve any instance by path (`game/Workspace/Baseplate`) or absolute address.
- 🌲 **Bounded tree traversal** — walk subtrees with configurable depth/node limits.
- 🧠 **VTable scanning** — find all live instances matching a given vtable pointer.
- 🎨 **Render asset enumeration** — pull mesh, texture, and surface IDs from a subtree.
- 📜 **Script tools** — list, inspect, decompile, source-search, and xref `Script` / `LocalScript` / `ModuleScript`.
- 🪝 **Raw bridge passthrough** — `bridge_request` exposes any action supported by the native bridge.

---

## Requirements

- **Windows** (the server communicates via a Windows named pipe — `\\.\pipe\charm_explorer_mcp` by default).
- **Python 3.10+**
- A running instance of the **Charm Explorer native bridge** (`explorer_mcp_bridge.cpp`) attached to the target Roblox process and listening on the configured pipe.

---

## Installation

Clone the repo and (optionally) create a virtualenv:

```bash
git clone [https://github.com/charmwtf/charm-explorer-mcp.git](https://github.com/charmwtf/charm-explorer-mcp.git)
cd charm-explorer-mcp

python -m venv .venv
.venv\Scripts\activate

```

No third-party Python dependencies are required — the server uses only the standard library.

Verify it runs:

```bash
python charm_explorer_mcp.py

```

It will block waiting for MCP messages on stdin. That's normal — your MCP client will spawn it.

---

## Configuration

The server is configured entirely through environment variables (see [Environment Variables](https://www.google.com/search?q=%23environment-variables)). The defaults work out of the box if the native bridge uses the default pipe name.

---

## Client Setup

Replace `C:\\path\\to\\charm_explorer_mcp.py` with the absolute path to the script on your machine. Use double backslashes in JSON.

### Claude Desktop

Edit your Claude Desktop config:

* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "charm-explorer": {
      "command": "python",
      "args": ["C:\\path\\to\\charm_explorer_mcp.py"],
      "env": {
        "CHARM_EXPLORER_PIPE_NAME": "\\\\.\\pipe\\charm_explorer_mcp"
      }
    }
  }
}

```

Restart Claude Desktop. The tools will appear under the 🔌 menu.

📚 [Claude Desktop MCP docs](https://modelcontextprotocol.io/quickstart/user)

---

### Claude Code

Add the server via the CLI:

```bash
claude mcp add charm-explorer -- python C:\path\to\charm_explorer_mcp.py

```

Or manually edit `~/.claude.json` / project `.mcp.json`:

```json
{
  "mcpServers": {
    "charm-explorer": {
      "command": "python",
      "args": ["C:\\path\\to\\charm_explorer_mcp.py"]
    }
  }
}

```

📚 [Claude Code MCP docs](https://docs.claude.com/en/docs/claude-code/mcp)

---

### Codex CLI

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.charm-explorer]
command = "python"
args = ["C:\\path\\to\\charm_explorer_mcp.py"]

[mcp_servers.charm-explorer.env]
CHARM_EXPLORER_PIPE_NAME = "\\\\.\\pipe\\charm_explorer_mcp"

```

Then launch Codex normally. Tools will be auto-discovered.

📚 [Codex MCP docs](https://github.com/openai/codex)

---

### VS Code (Continue / Cline / Roo)

For **[Cline](https://github.com/cline/cline)** or **[Roo Code](https://github.com/RooCodeInc/Roo-Code)**, open the extension settings and add:

```json
{
  "mcpServers": {
    "charm-explorer": {
      "command": "python",
      "args": ["C:\\path\\to\\charm_explorer_mcp.py"],
      "disabled": false,
      "autoApprove": []
    }
  }
}

```

For **native VS Code MCP support** (`.vscode/mcp.json`):

```json
{
  "servers": {
    "charm-explorer": {
      "type": "stdio",
      "command": "python",
      "args": ["C:\\path\\to\\charm_explorer_mcp.py"]
    }
  }
}

```

📚 [VS Code MCP docs](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)

---

### Cursor

Add to `~/.cursor/mcp.json` (or `.cursor/mcp.json` in your project):

```json
{
  "mcpServers": {
    "charm-explorer": {
      "command": "python",
      "args": ["C:\\path\\to\\charm_explorer_mcp.py"]
    }
  }
}

```

📚 [Cursor MCP docs](https://docs.cursor.com/context/model-context-protocol)

---

### Zed

In your Zed `settings.json`:

```json
{
  "context_servers": {
    "charm-explorer": {
      "command": {
        "path": "python",
        "args": ["C:\\path\\to\\charm_explorer_mcp.py"]
      }
    }
  }
}

```

📚 [Zed context servers docs](https://zed.dev/docs/assistant/context-servers)

---

## Tools

| Tool | Description |
| --- | --- |
| `status` | Get bridge status — DataModel, Players, Workspace, output dir. |
| `scan_vtable_instances` | Scan process memory for instances whose vtable matches a given address. |
| `get_instance` | Resolve an instance by path or address; optionally include children. |
| `list_children` | List direct children of an instance. |
| `get_tree` | Build a bounded subtree (configurable depth + node cap). |
| `search_instances` | Substring/class search under a subtree. |
| `inspect_render_assets` | Pull mesh, texture, and surface asset IDs under a subtree. |
| `list_scripts` | Enumerate `Script` / `LocalScript` / `ModuleScript` under a root. |
| `inspect_script` | Inspect bytecode/decompiler candidates for a single script. |
| `decompile_script` | Decompile a script and optionally save output to disk. |
| `search_script_source` | Decompile scripts under a root and grep their source / refs / strings. |
| `script_xrefs` | Find scripts that reference a given target script. |
| `bridge_request` | Raw passthrough to the native bridge (escape hatch). |

All instance-targeting tools accept either:

```json
{ "path": "game/Workspace/Baseplate" }

```

or:

```json
{ "address": "0x1A2B3C4D5E" }

```

---

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `CHARM_EXPLORER_PIPE_NAME` | `\\.\pipe\charm_explorer_mcp` | Windows named pipe exposed by the native bridge. |
| `CHARM_EXPLORER_MCP_PROTOCOL_VERSION` | `2024-11-05` | MCP protocol version advertised during `initialize`. |

---

## Troubleshooting

**`FileNotFoundError` / pipe errors**
The native bridge isn't running, or it's listening on a different pipe name. Make sure `explorer_mcp_bridge.cpp` is attached to the Roblox process and the `CHARM_EXPLORER_PIPE_NAME` matches.

**Tools don't appear in the client**

* Check the client's MCP logs (Claude Desktop: `%APPDATA%\Claude\logs\`).
* Confirm `python` is on your `PATH` — use a full path like `C:\\Python312\\python.exe` if not.
* Verify the script path uses escaped backslashes in JSON.

**`stream closed before the full payload was read`**
The bridge crashed or disconnected mid-response. Restart the native bridge.

**Server hangs**
That's expected when launched manually — it's waiting for JSON-RPC messages on stdin. Launch it through an MCP client.

---

## License

MIT — see [LICENSE](https://www.google.com/search?q=./LICENSE).

---

## Related

* [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
* [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)
* [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

```

```
