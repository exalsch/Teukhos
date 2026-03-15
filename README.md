# Teukhos

> *You describe the tool. Teukhos forges it as MCP.*

**Spawn production-ready MCP servers from a single YAML file. No Python required.**

```bash
pip install teukhos
teukhos serve git-tools.yaml
```

That's it. Your CLI tools are now callable by any AI agent.

---

## The Problem

The MCP ecosystem has a critical gap:

| What exists | What's missing |
|---|---|
| Raw FastMCP — write Python | **Config-as-code → running MCP server** |
| `any-cli-mcp-server` — scrapes `--help` | **Structured, typed CLI → tool mapping** |
| Enterprise gateways (Bifrost, MCPX) | **Lightweight, developer-owned, open-source** |
| Visual builders (Langflow, n8n) | **CI/CD-native, GitOps-friendly runtime** |

Teukhos fills this gap. Define your tools in YAML. Run one command. Done.

---

## 30-Second Quickstart

**Install:**
```bash
pip install teukhos
# or: uvx teukhos
```

**Create `teukhos.yaml`:**
```yaml
forge:
  name: "my-tools"

tools:
  - name: git_log
    description: "Show recent git commits"
    adapter: cli
    cli:
      command: git
      subcommand: [log, --oneline]
    args:
      - name: count
        type: integer
        flag: "-n"
        default: 10
    output:
      type: stdout
```

**Serve:**
```bash
teukhos serve teukhos.yaml
```

**Register with your AI client:**
```bash
teukhos install teukhos.yaml                           # auto-detect & prompt
teukhos install teukhos.yaml --client cursor            # specific client
teukhos install teukhos.yaml --client claude-code --project  # project-level
```

Ask Claude: *"Show me the last 5 commits"* — it uses the tool.

---

## How It Works

```
teukhos.yaml
     │
     ▼
┌─────────────┐
│   Parser    │  Pydantic validation, type checking, early error detection
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Adapter    │  Builds async handler functions per tool
│  Factory    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FastMCP    │  Registers tools with correct JSON Schema
│  Builder    │  (inferred from your arg definitions)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  MCP Server │  stdio or HTTP — ready for Claude, Cursor, any MCP client
└─────────────┘
```

---

## CLI Reference

```
teukhos serve [config]            Start the MCP server
teukhos validate [config]         Validate config, exit 0/1 — use in CI
teukhos install [config]          Register with MCP client(s)
teukhos uninstall <server-name>   Remove from MCP client(s)
teukhos clients                   List supported clients & detection status
teukhos wait-ready                Poll /health until ready — use in CI
teukhos version                   Print version
teukhos discover <binary>         (Coming soon) Auto-generate config from --help
```

**Options for `serve`:**
```
--transport  -t    Override transport: stdio | http  (default: from config)
--port       -p    Override HTTP port                (default: 8765)
```

**Options for `install`:**
```
--client  -c    Target a specific client by slug (e.g., cursor, claude-code)
--all           Install for all detected clients
--project       Use project-level config (e.g., .cursor/mcp.json in cwd)
--url           Remote server URL — enables HTTP mode
--key           API key for HTTP mode (default: "env:TEUKHOS_API_KEY")
```

**Options for `uninstall`:**
```
--client  -c    Target a specific client by slug
--all           Remove from all detected clients
--project       Target project-level config
```

**Config file names:** Teukhos looks for `teukhos.yaml` by default. Legacy `mcp-forge.yaml` is accepted automatically with a deprecation note.

---

## Supported Clients

Teukhos can register with these MCP-compatible AI clients:

| Client | Slug | Project Scope |
|--------|------|:------------:|
| Claude Desktop | `claude-desktop` | — |
| Claude Code | `claude-code` | Yes |
| Cursor | `cursor` | Yes |
| GitHub Copilot / VS Code | `github-copilot` | Yes |
| Gemini CLI | `gemini-cli` | — |
| Codex | `codex` | — |
| Windsurf | `windsurf` | Yes |
| Cline | `cline` | Yes |
| Roo Code | `roo-code` | Yes |
| Continue.dev | `continue` | Yes |
| Kiro | `kiro` | Yes |
| Auggie | `auggie` | — |
| CodeBuddy | `codebuddy` | — |
| OpenCode | `opencode` | — |
| Trae | `trae` | Yes |

```bash
teukhos clients              # see which are detected on your system
teukhos install --all         # register with all detected clients
```

---

## Running Multiple Servers

You can run multiple Teukhos servers in parallel on the same machine. Each config gets a unique server name derived from its `forge.name`, so they don't overwrite each other in client configs.

**stdio (no conflicts — each client spawns its own process):**
```bash
teukhos install git-tools.yaml --client cursor       # registers teukhos-git-tools
teukhos install dev-tools.yaml --client cursor        # registers teukhos-dev-tools
```

**HTTP (use different ports):**
```bash
teukhos serve git-tools.yaml --transport http --port 8765 &
teukhos serve dev-tools.yaml --transport http --port 8766 &
```

---

## Full Config Reference

```yaml
forge:
  name: "my-toolset"          # MCP server identity
  version: "1.0.0"
  description: "What this server does"

server:
  transport: stdio             # stdio | http
  host: "127.0.0.1"           # use 0.0.0.0 for remote (add auth!)
  port: 8765
  cors_origins: ["*"]         # CORS origins for HTTP (default: none)

auth:
  mode: none                   # none | api_key
  api_keys:
    - "env:TEUKHOS_API_KEY"    # reads from environment variable (recommended)
    - "env:MY_CUSTOM_KEY"      # any env var name with env: prefix
    - "literal-key-here"       # or use a literal string directly

tools:
  - name: tool_name            # snake_case — used as MCP tool ID
    description: "What the LLM reads to decide when to call this tool"
    adapter: cli               # cli is the only adapter in v0.2

    cli:
      command: "mybinary"      # must be on PATH or absolute path
      subcommand: []           # e.g. ["log", "--oneline"] for git
      timeout_seconds: 30
      working_dir: null        # defaults to cwd
      env: {}                  # extra env vars for this tool

    args:
      - name: arg_name
        type: string           # string | integer | number | boolean
        description: "Shown to the LLM"
        required: false
        flag: "--flag"         # CLI flag: -f or --flag
        positional: false      # true = append at end of command
        default: null
        enum: []               # restrict to allowed values
        secret: false          # redact from logs

    output:
      type: stdout             # stdout | stderr | json_field | exit_code
      field: null              # for json_field: dot-notation path e.g. "data.items"
      exit_codes:              # for exit_code type: map codes to messages
        0: "Success"
        1: "Not found"
```

---

## Example Configs

### Git Tools
```yaml
forge:
  name: "git-tools"

tools:
  - name: git_log
    description: "Show recent git commits"
    adapter: cli
    cli:
      command: git
      subcommand: [log, --oneline]
    args:
      - name: count
        type: integer
        flag: "-n"
        default: 10
    output:
      type: stdout

  - name: git_status
    description: "Show working tree status"
    adapter: cli
    cli:
      command: git
      subcommand: [status, --short]
    output:
      type: stdout

  - name: git_diff
    description: "Show diff of current changes"
    adapter: cli
    cli:
      command: git
      subcommand: [diff]
    args:
      - name: staged
        type: boolean
        description: "Show staged changes only"
        flag: "--staged"
    output:
      type: stdout
```

### System Tools
```yaml
forge:
  name: "sysops"

tools:
  - name: disk_usage
    description: "Show disk usage for a path"
    adapter: cli
    cli:
      command: du
      subcommand: ["-sh"]
    args:
      - name: path
        type: string
        positional: true
        default: "."
    output:
      type: stdout

  - name: ping_host
    description: "Check if a host is reachable"
    adapter: cli
    cli:
      command: ping
      subcommand: ["-c", "3"]
      timeout_seconds: 15
    args:
      - name: host
        type: string
        required: true
        positional: true
    output:
      type: exit_code
      exit_codes:
        0: "Host is reachable"
        1: "Host is unreachable"
```

### JSON Output
```yaml
  - name: get_video_info
    description: "Get video metadata as JSON"
    adapter: cli
    cli:
      command: ffprobe
      subcommand: ["-v", "quiet", "-print_format", "json", "-show_format"]
    args:
      - name: input_file
        type: string
        required: true
        positional: true
    output:
      type: json_field
      field: "format.duration"   # extract a specific field
```

---

## Remote Server / HTTP Transport

Run Teukhos as a network-accessible server:

```yaml
# remote-server.yaml
server:
  transport: http
  host: "0.0.0.0"
  port: 8765

auth:
  mode: api_key
  api_keys:
    - "env:TEUKHOS_API_KEY"
```

```bash
# Start the server
export TEUKHOS_API_KEY="your-secret-key"
teukhos serve remote-server.yaml

# Connect a client (from any machine)
teukhos install --client cursor --url http://server-ip:8765/mcp
```

### API Key Resolution

Keys in config use the `env:` prefix convention:

| Config Value | Resolved To |
|---|---|
| `"env:TEUKHOS_API_KEY"` | Value of `$TEUKHOS_API_KEY` environment variable |
| `"env:MY_CUSTOM_KEY"` | Value of `$MY_CUSTOM_KEY` environment variable |
| `"my-literal-key"` | Used as-is (not recommended for production) |

### Deployment Behind a Reverse Proxy

For production, run behind nginx or Caddy for TLS termination:

```nginx
# nginx example
server {
    listen 443 ssl;
    server_name mcp.example.com;

    ssl_certificate /etc/letsencrypt/live/mcp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
    }
}
```

---

## CI/CD Integration

### GitHub Actions
```yaml
- name: Install Teukhos
  run: pip install teukhos

- name: Validate config
  run: teukhos validate teukhos.yaml

- name: Start MCP server
  run: |
    teukhos serve teukhos.yaml --transport http --port 8765 &
    teukhos wait-ready --timeout 30

- name: Run agent tasks
  run: |
    claude --mcp http://localhost:8765/mcp \
      "Analyse the git log and summarise what changed this week"

- name: Teardown
  if: always()
  run: pkill -f "teukhos serve" || true
```

### Docker
```dockerfile
FROM python:3.12-slim
RUN pip install teukhos
COPY teukhos.yaml .
EXPOSE 8765
HEALTHCHECK CMD teukhos wait-ready --timeout 5
CMD ["teukhos", "serve", "--transport", "http"]
```

### Manual Client Configuration

If you prefer manual setup, add to your client's MCP config:

**stdio (local):**
```json
{
  "mcpServers": {
    "teukhos-my-tools": {
      "command": "teukhos",
      "args": ["serve", "/path/to/teukhos.yaml"]
    }
  }
}
```

**HTTP (remote):**
```json
{
  "mcpServers": {
    "teukhos-remote": {
      "url": "http://server:8765/mcp",
      "headers": {
        "Authorization": "Bearer ${TEUKHOS_API_KEY}"
      }
    }
  }
}
```

Or use the install command: `teukhos install teukhos.yaml --client cursor`

---

## Roadmap

### v0.3 — Current
- Multi-client installer: 15 MCP clients supported
- Project-level and global-level installation scope
- `teukhos install` with auto-detect, `--client`, `--all`, `--project`, `--url`
- `teukhos uninstall` to remove registrations
- `teukhos clients` to list supported clients
- HTTP Streamable transport with startup banner
- `env:` prefix API key resolution
- CORS configuration for HTTP transport
- Full authentication middleware (Bearer token)

### v0.4 — Production Ready
- `rest` adapter (wrap any HTTP endpoint)
- `shell` adapter (inline bash/pwsh scripts)
- Hot reload — save YAML, tools update without restart
- `teukhos discover <binary>` — AI-powered config generation from `--help`
- Streaming output support
- Lock file (`teukhos.lock`) for reproducible deployments

### v0.5 — The Platform
- OAuth 2.1 + JWT auth
- mTLS support for enterprise deployments
- Tool-level RBAC
- Append-only audit log
- Embedded web UI — dark glass, real-time tool call visualization
- Bidirectional YAML to visual editor sync
- OpenAPI auto-import adapter
- Tool composition / mini pipelines
- Prometheus metrics at `/metrics`
- Public registry: `teukhos install registry://community/git-tools`

---

## Why Teukhos?

You provide the MCP specification. Teukhos does the forging.

---

## Contributing

```bash
git clone https://github.com/MihaiCiprianChezan/teukhos
cd teukhos
pip install -e ".[dev]"
pytest
```

Pull requests welcome.

---

## License

MIT — see [LICENSE](LICENSE).

*Built by [Mihai Ciprian Chezan](https://github.com/MihaiCiprianChezan)*
