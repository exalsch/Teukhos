# Changelog

All notable changes to Teukhos are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.2.0] — 2026-03-15

### Changed
- **Project renamed from MCPForge to Teukhos** — unique name, clean namespace
  across PyPI, npm, GitHub, and all major registries
- CLI command changed from `mcp-forge` to `teukhos`
- Default config filename changed from `mcp-forge.yaml` to `teukhos.yaml`
- Legacy `mcp-forge.yaml` still accepted automatically with a deprecation note
- Package name on PyPI changed from `mcpforge` to `teukhos`
- All internal imports updated from `mcpforge.*` to `teukhos.*`
- `ForgeInfo.name` default updated to `teukhos-server`
- `install` command now registers as `teukhos-<name>` in Claude Desktop config
- Version bumped to 0.2.0 to mark the identity change cleanly

### Added
- `httpx` added as an explicit dependency (was implicit via fastmcp)
- Backward-compatible config file resolution (`_resolve_config` in CLI)
- `[tool.hatch.build.targets.wheel]` section in `pyproject.toml`
- Project URLs (Homepage, Repository, Issues) in `pyproject.toml`
- PyPI classifiers
- GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- This CHANGELOG

### Fixed
- Boolean arg handling: cleaned up redundant condition in `_build_command`

---

## [0.1.0] — 2026-03-11

### Added
- Initial working PoC under the name MCPForge
- Pydantic config models for `mcp-forge.yaml`
- `cli` adapter with typed arg mapping (flags, positional, boolean)
- Output mapping: `stdout`, `stderr`, `json_field`, `exit_code`
- FastMCP server generation at runtime with dynamic function signatures
- `stdio` and `http` (streamable-http) transports
- `api_key` auth mode
- `serve`, `validate`, `version`, `wait-ready`, `install`, `discover` CLI commands
- Rich startup banner
- Security warning for unauthenticated 0.0.0.0 bindings
- Health endpoint `/health`
- Example configs: `git-tools.yaml`, `dev-tools.yaml`, `media-tools.yaml`
- Full test suite: unit + integration tests
- Claude Desktop integration via `install` command
