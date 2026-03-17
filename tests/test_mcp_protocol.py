"""MCP protocol-level integration tests.

These tests exercise the FULL MCP JSON-RPC protocol path by using FastMCP's
Client class, which communicates via in-memory streams (the same JSON-RPC
framing that stdio and HTTP transports use). This catches bugs that direct
tool.fn() calls miss — e.g. parameter serialisation, stdin inheritance,
dynamic signature introspection issues.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastmcp import Client

from teukhos.config import (
    ArgConfig,
    ArgType,
    CLIAdapterConfig,
    ForgeConfig,
    ForgeInfo,
    OutputConfig,
    OutputType,
    ToolConfig,
    load_config,
)
from teukhos.engine import build_server

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _python_cmd() -> str:
    """Return the Python executable name (works cross-platform)."""
    return sys.executable


def _make_server(tools: list[ToolConfig], name: str = "test") -> Client:
    """Build a FastMCP server from tool configs and return a Client."""
    config = ForgeConfig(forge=ForgeInfo(name=name), tools=tools)
    bundle = build_server(config)
    return Client(bundle.mcp)


def _echo_tool(name: str = "echo_tool") -> ToolConfig:
    """A cross-platform echo tool using python -c."""
    return ToolConfig(
        name=name,
        description="Echo a message",
        adapter="cli",
        cli=CLIAdapterConfig(
            command=_python_cmd(),
            subcommand=["-c", "import sys; print(sys.argv[1])"],
        ),
        args=[
            ArgConfig(
                name="message",
                type=ArgType.string,
                required=True,
                positional=True,
            )
        ],
        output=OutputConfig(),
    )


# ---------------------------------------------------------------------------
# Core protocol tests
# ---------------------------------------------------------------------------

class TestMCPProtocolBasics:
    """Verify the MCP protocol handshake, tool listing, and basic calls."""

    @pytest.mark.asyncio
    async def test_client_connects_and_pings(self):
        """Client can connect to server and ping it."""
        client = _make_server([_echo_tool()])
        async with client:
            assert await client.ping() is True

    @pytest.mark.asyncio
    async def test_list_tools_returns_registered_tools(self):
        """tools/list returns all registered tools with correct names."""
        tool_a = _echo_tool("tool_a")
        tool_b = _echo_tool("tool_b")
        client = _make_server([tool_a, tool_b])
        async with client:
            tools = await client.list_tools()
            names = {t.name for t in tools}
            assert names == {"tool_a", "tool_b"}

    @pytest.mark.asyncio
    async def test_tool_schema_has_correct_params(self):
        """Tool JSON schema reflects the YAML-defined arguments."""
        tool = ToolConfig(
            name="multi_arg",
            description="Tool with multiple arg types",
            adapter="cli",
            cli=CLIAdapterConfig(command=_python_cmd(), subcommand=["-c", "pass"]),
            args=[
                ArgConfig(name="name", type=ArgType.string, required=True),
                ArgConfig(name="count", type=ArgType.integer, required=False, default=5),
                ArgConfig(name="verbose", type=ArgType.boolean, required=False, flag="--verbose"),
            ],
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            tools = await client.list_tools()
            schema = tools[0].inputSchema
            assert "name" in schema["properties"]
            assert schema["required"] == ["name"]

    @pytest.mark.asyncio
    async def test_call_tool_returns_text_content(self):
        """tools/call returns a TextContent block with the tool output."""
        client = _make_server([_echo_tool()])
        async with client:
            result = await client.call_tool("echo_tool", {"message": "hello protocol"})
            assert result.is_error is False
            text = result.content[0].text
            assert "hello protocol" in text


# ---------------------------------------------------------------------------
# Command execution tests (through MCP protocol)
# ---------------------------------------------------------------------------

class TestCommandExecution:
    """Verify that CLI commands actually execute through the MCP protocol."""

    @pytest.mark.asyncio
    async def test_python_script_execution(self):
        """Execute a Python one-liner through MCP."""
        tool = ToolConfig(
            name="py_calc",
            description="Calculate with Python",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c"],
            ),
            args=[
                ArgConfig(name="expr", type=ArgType.string, required=True, positional=True),
            ],
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("py_calc", {"expr": "print(2 + 2)"})
            assert "4" in result.content[0].text

    @pytest.mark.asyncio
    async def test_git_command_execution(self):
        """Execute a real git command through MCP."""
        tool = ToolConfig(
            name="git_ver",
            description="Get git version",
            adapter="cli",
            cli=CLIAdapterConfig(command="git", subcommand=["--version"]),
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("git_ver", {})
            assert "git version" in result.content[0].text

    @pytest.mark.asyncio
    async def test_command_with_arguments(self):
        """Tool arguments are correctly passed to the subprocess."""
        tool = ToolConfig(
            name="git_log",
            description="Git log",
            adapter="cli",
            cli=CLIAdapterConfig(command="git", subcommand=["log", "--oneline"]),
            args=[
                ArgConfig(
                    name="count",
                    type=ArgType.integer,
                    required=False,
                    flag="-n",
                    default=2,
                )
            ],
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("git_log", {"count": 3})
            lines = result.content[0].text.strip().split("\n")
            assert len(lines) <= 3

    @pytest.mark.asyncio
    async def test_boolean_flag_argument(self):
        """Boolean flag args are passed correctly as CLI flags."""
        tool = ToolConfig(
            name="git_branch",
            description="List branches",
            adapter="cli",
            cli=CLIAdapterConfig(command="git", subcommand=["branch"]),
            args=[
                ArgConfig(
                    name="all",
                    type=ArgType.boolean,
                    required=False,
                    flag="--all",
                )
            ],
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            # Without flag
            result = await client.call_tool("git_branch", {})
            assert isinstance(result.content[0].text, str)
            # With flag
            result_all = await client.call_tool("git_branch", {"all": True})
            assert isinstance(result_all.content[0].text, str)

    @pytest.mark.asyncio
    async def test_positional_argument(self):
        """Positional args are appended at the end of the command."""
        tool = ToolConfig(
            name="py_print",
            description="Print a value",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", "import sys; print(f'GOT:{sys.argv[1]}')"],
            ),
            args=[
                ArgConfig(
                    name="value",
                    type=ArgType.string,
                    required=True,
                    positional=True,
                )
            ],
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("py_print", {"value": "test123"})
            assert "GOT:test123" in result.content[0].text


# ---------------------------------------------------------------------------
# stdin isolation (the critical fix)
# ---------------------------------------------------------------------------

class TestStdinIsolation:
    """Verify that tool subprocess stdin is isolated from the MCP protocol stream.

    This is the critical regression test for the anyio.run_process stdin
    inheritance bug. If stdin is not properly redirected to DEVNULL, these
    tests will hang or produce corrupt results.
    """

    @pytest.mark.asyncio
    async def test_subprocess_does_not_read_stdin(self):
        """A tool that tries to read stdin should get EOF, not MCP data."""
        tool = ToolConfig(
            name="stdin_test",
            description="Try to read stdin",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=[
                    "-c",
                    "import sys; data = sys.stdin.read(); print(f'stdin_bytes:{len(data)}')",
                ],
            ),
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("stdin_test", {})
            # stdin should be /dev/null -> 0 bytes
            assert "stdin_bytes:0" in result.content[0].text

    @pytest.mark.asyncio
    async def test_multiple_sequential_tool_calls(self):
        """Multiple tool calls in sequence should all succeed (no stdin corruption)."""
        client = _make_server([_echo_tool()])
        async with client:
            for i in range(5):
                result = await client.call_tool("echo_tool", {"message": f"call-{i}"})
                assert f"call-{i}" in result.content[0].text

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Multiple concurrent tool calls should not interfere with each other."""
        import asyncio

        client = _make_server([_echo_tool()])
        async with client:
            tasks = [
                client.call_tool("echo_tool", {"message": f"concurrent-{i}"})
                for i in range(5)
            ]
            results = await asyncio.gather(*tasks)
            texts = [r.content[0].text for r in results]
            for i in range(5):
                assert any(f"concurrent-{i}" in t for t in texts)


# ---------------------------------------------------------------------------
# Error handling through MCP protocol
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Verify error handling works correctly through the MCP protocol."""

    @pytest.mark.asyncio
    async def test_nonexistent_command_returns_error(self):
        """A tool with a missing binary returns a clear error message."""
        tool = ToolConfig(
            name="missing_cmd",
            description="Command does not exist",
            adapter="cli",
            cli=CLIAdapterConfig(command="nonexistent_binary_xyz_12345"),
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool_mcp("missing_cmd", {})
            text = result.content[0].text
            assert "not found" in text.lower() or "error" in text.lower()

    @pytest.mark.asyncio
    async def test_command_nonzero_exit_returns_error(self):
        """A tool that exits non-zero returns an error message."""
        tool = ToolConfig(
            name="fail_tool",
            description="Always fails",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", "import sys; print('oops', file=sys.stderr); sys.exit(1)"],
            ),
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool_mcp("fail_tool", {})
            text = result.content[0].text
            assert "Error" in text or "oops" in text

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self):
        """A tool that exceeds its timeout returns a timeout error."""
        tool = ToolConfig(
            name="slow_tool",
            description="Sleeps too long",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", "import time; time.sleep(60)"],
                timeout_seconds=2,
            ),
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool_mcp("slow_tool", {})
            text = result.content[0].text
            assert "timed out" in text.lower() or "timeout" in text.lower()

    @pytest.mark.asyncio
    async def test_exit_code_mapping(self):
        """Exit code mapping returns configured human-readable messages."""
        tool = ToolConfig(
            name="check_exit",
            description="Test exit codes",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c"],
            ),
            args=[
                ArgConfig(name="code", type=ArgType.string, positional=True, required=True)
            ],
            output=OutputConfig(
                type=OutputType.exit_code,
                exit_codes={0: "All good", 1: "Something failed"},
            ),
        )
        client = _make_server([tool])
        async with client:
            r0 = await client.call_tool("check_exit", {"code": "import sys; sys.exit(0)"})
            assert r0.content[0].text == "All good"
            r1 = await client.call_tool("check_exit", {"code": "import sys; sys.exit(1)"})
            assert r1.content[0].text == "Something failed"


# ---------------------------------------------------------------------------
# Output mapping through MCP protocol
# ---------------------------------------------------------------------------

class TestOutputMapping:
    """Verify output mapping works correctly through the MCP protocol."""

    @pytest.mark.asyncio
    async def test_stdout_output(self):
        """stdout output type returns subprocess stdout."""
        tool = ToolConfig(
            name="stdout_tool",
            description="Returns stdout",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", "print('hello stdout')"],
            ),
            output=OutputConfig(type=OutputType.stdout),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("stdout_tool", {})
            assert "hello stdout" in result.content[0].text

    @pytest.mark.asyncio
    async def test_stderr_output(self):
        """stderr output type returns subprocess stderr."""
        tool = ToolConfig(
            name="stderr_tool",
            description="Returns stderr",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", "import sys; print('hello stderr', file=sys.stderr)"],
            ),
            output=OutputConfig(type=OutputType.stderr),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("stderr_tool", {})
            assert "hello stderr" in result.content[0].text

    @pytest.mark.asyncio
    async def test_json_field_extraction(self):
        """json_field output type extracts a field from JSON stdout."""
        tool = ToolConfig(
            name="json_tool",
            description="Returns JSON",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", 'import json; print(json.dumps({"name": "teukhos", "version": "1.0"}))'],
            ),
            output=OutputConfig(type=OutputType.json_field, field="name"),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("json_tool", {})
            assert result.content[0].text == "teukhos"

    @pytest.mark.asyncio
    async def test_json_nested_field_extraction(self):
        """json_field with dot notation extracts nested fields."""
        tool = ToolConfig(
            name="nested_json_tool",
            description="Returns nested JSON",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", 'import json; print(json.dumps({"data": {"count": 42}}))'],
            ),
            output=OutputConfig(type=OutputType.json_field, field="data.count"),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("nested_json_tool", {})
            assert result.content[0].text == "42"


# ---------------------------------------------------------------------------
# Example YAML config tests through MCP protocol
# ---------------------------------------------------------------------------

class TestExampleConfigs:
    """Test real example YAML configs through the full MCP protocol."""

    @pytest.mark.asyncio
    async def test_all_configs_ping_through_protocol(self):
        """Every example config's ping tool works through the MCP protocol."""
        for yaml_file in sorted(EXAMPLES_DIR.glob("*.yaml")):
            config = load_config(yaml_file)
            bundle = build_server(config)
            async with Client(bundle.mcp) as client:
                tools = await client.list_tools()
                tool_names = [t.name for t in tools]
                assert "ping" in tool_names, f"{yaml_file.name}: no ping tool"
                result = await client.call_tool("ping", {})
                assert "pong" in result.content[0].text.lower(), (
                    f"{yaml_file.name}: ping returned {result.content[0].text!r}"
                )

    @pytest.mark.asyncio
    async def test_git_tools_through_protocol(self):
        """git-tools.yaml: call git_log and git_status through MCP protocol."""
        config = load_config(EXAMPLES_DIR / "git-tools.yaml")
        bundle = build_server(config)
        async with Client(bundle.mcp) as client:
            # git_log with count argument
            result = await client.call_tool("git_log", {"count": 2})
            lines = result.content[0].text.strip().split("\n")
            assert len(lines) <= 2

            # git_status with no arguments
            result = await client.call_tool("git_status", {})
            assert isinstance(result.content[0].text, str)

    @pytest.mark.asyncio
    async def test_dev_tools_run_command_through_protocol(self):
        """dev-tools.yaml: run_command executes arbitrary commands through MCP."""
        config = load_config(EXAMPLES_DIR / "dev-tools.yaml")
        bundle = build_server(config)
        async with Client(bundle.mcp) as client:
            result = await client.call_tool(
                "run_command", {"command": "echo protocol-test-ok"}
            )
            assert "protocol-test-ok" in result.content[0].text

    @pytest.mark.asyncio
    async def test_all_configs_list_tools_through_protocol(self):
        """Every example config exposes at least 2 tools via MCP protocol."""
        for yaml_file in sorted(EXAMPLES_DIR.glob("*.yaml")):
            config = load_config(yaml_file)
            bundle = build_server(config)
            async with Client(bundle.mcp) as client:
                tools = await client.list_tools()
                assert len(tools) >= 2, (
                    f"{yaml_file.name}: only {len(tools)} tools"
                )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and regression tests."""

    @pytest.mark.asyncio
    async def test_tool_with_no_args(self):
        """A tool with zero arguments works through the protocol."""
        tool = ToolConfig(
            name="no_args",
            description="No arguments",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", "print('no args ok')"],
            ),
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("no_args", {})
            assert "no args ok" in result.content[0].text

    @pytest.mark.asyncio
    async def test_tool_with_special_characters_in_output(self):
        """Tool output with special characters is preserved."""
        tool = ToolConfig(
            name="special_chars",
            description="Output with special chars",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", r"print('line1\nline2\ttab')"],
            ),
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("special_chars", {})
            text = result.content[0].text
            assert "line1" in text
            assert "line2" in text

    @pytest.mark.asyncio
    async def test_tool_with_large_output(self):
        """Tool that produces large output doesn't crash the protocol."""
        tool = ToolConfig(
            name="large_output",
            description="Lots of output",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", "print('x' * 10000)"],
            ),
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("large_output", {})
            assert len(result.content[0].text) >= 10000

    @pytest.mark.asyncio
    async def test_tool_with_env_vars(self):
        """Tool with custom environment variables works."""
        tool = ToolConfig(
            name="env_tool",
            description="Check env var",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", "import os; print(os.environ.get('TEST_VAR', 'NOT_SET'))"],
                env={"TEST_VAR": "hello_env"},
            ),
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            result = await client.call_tool("env_tool", {})
            assert "hello_env" in result.content[0].text

    @pytest.mark.asyncio
    async def test_tool_with_optional_arg_default(self):
        """Optional args use their default value when not provided."""
        tool = ToolConfig(
            name="default_arg",
            description="Has default",
            adapter="cli",
            cli=CLIAdapterConfig(
                command=_python_cmd(),
                subcommand=["-c", "import sys; print(f'count={sys.argv[1]}' if len(sys.argv) > 1 else 'count=default')"],
            ),
            args=[
                ArgConfig(
                    name="count",
                    type=ArgType.integer,
                    required=False,
                    positional=True,
                    default=10,
                )
            ],
            output=OutputConfig(),
        )
        client = _make_server([tool])
        async with client:
            # Without arg - should use default
            result = await client.call_tool("default_arg", {})
            assert "count=10" in result.content[0].text
            # With arg
            result = await client.call_tool("default_arg", {"count": 42})
            assert "count=42" in result.content[0].text

    @pytest.mark.asyncio
    async def test_unsupported_adapter_type_silently_skipped(self):
        """Tools with unsupported adapter types are not registered."""
        tools = [
            _echo_tool("good_tool"),
            ToolConfig(
                name="bad_tool",
                description="Unsupported adapter",
                adapter="unsupported",
                output=OutputConfig(),
            ),
        ]
        client = _make_server(tools)
        async with client:
            listed = await client.list_tools()
            names = {t.name for t in listed}
            assert "good_tool" in names
            assert "bad_tool" not in names
