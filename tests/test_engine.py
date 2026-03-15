"""Tests for the FastMCP engine."""

from pathlib import Path

import pytest

from teukhos.config import load_config
from teukhos.engine import build_server


def test_build_server_from_git_tools():
    config = load_config(Path(__file__).parent.parent / "examples" / "git-tools.yaml")
    server = build_server(config)
    assert server is not None
    assert server.name == "git-tools"


def test_build_server_from_dev_tools():
    config = load_config(Path(__file__).parent.parent / "examples" / "dev-tools.yaml")
    server = build_server(config)
    assert server is not None
    assert server.name == "dev-tools"


@pytest.mark.asyncio
async def test_tool_execution_echo():
    """Test that a dynamically built tool actually executes correctly."""
    from teukhos.config import (
        ArgConfig,
        ArgType,
        CLIAdapterConfig,
        ForgeConfig,
        ForgeInfo,
        OutputConfig,
        ToolConfig,
    )

    config = ForgeConfig(
        forge=ForgeInfo(name="test-echo"),
        tools=[
            ToolConfig(
                name="echo_tool",
                description="Echo a message",
                adapter="cli",
                cli=CLIAdapterConfig(command="echo"),
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
        ],
    )
    server = build_server(config)

    tool = await server.get_tool("echo_tool")
    assert tool is not None
    result = await tool.fn(message="hello from test")
    assert "hello from test" in result
