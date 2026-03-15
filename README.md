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

**Add to Claude Desktop:**
```bash
teukhos install teukhos.yaml --client claude-desktop
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
teukhos serve [config]          Start the MCP server
teukhos validate [config]       Validate config, exit 0/1 — use in CI
teukhos install [config]        Register with Claude Desktop
teukhos wait-ready              Poll /health until ready — use in CI pipelines
teukhos version                 Print version
teukhos discover <binary>       (Coming v0.3) Auto-generate config from --help
```

**Options for `serve`:**
```
--transport  -t    Override transport: stdio | http  (default: from config)
--port       -p    Override HTTP port                (default: 8765)
```

**Config file names:** Teukhos looks for `teukhos.yaml` by default. Legacy `mcp-forge.yaml` is accepted automatically with a deprecation note.

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

auth:
  mode: none                   # none | api_key
  api_keys:
    - "${MY_API_KEY}"

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

### Claude Desktop (manual)
```json
{
  "mcpServers": {
    "teukhos-git": {
      "command": "teukhos",
      "args": ["serve", "/path/to/git-tools.yaml"]
    }
  }
}
```

Or use the install command: `teukhos install git-tools.yaml --client claude-desktop`

---

## Roadmap

### v0.2 — Current
- YAML parser + Pydantic schema validation
- `cli` adapter with typed arg mapping
- Output mapping: `stdout`, `stderr`, `json_field`, `exit_code`
- FastMCP server generation at runtime
- `stdio` and `http` transports
- `api_key` auth
- `teukhos validate` for CI linting
- `teukhos wait-ready` for CI health checks
- `teukhos install` for Claude Desktop registration
- Health endpoint `/health`

### v0.3 — Production Ready
- `rest` adapter (wrap any HTTP endpoint)
- `shell` adapter (inline bash/pwsh scripts)
- Hot reload — save YAML, tools update without restart
- `teukhos discover <binary>` — AI-powered config generation from `--help`
- OAuth 2.1 + JWT auth
- Tool-level RBAC
- Append-only audit log
- Streaming output support
- Lock file (`teukhos.lock`) for reproducible deployments

### v0.4 — The Platform
- Embedded web UI — dark glass, real-time tool call visualization
- Bidirectional YAML ↔ visual editor sync
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
