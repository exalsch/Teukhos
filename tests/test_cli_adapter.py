"""Tests for the CLI adapter."""

import pytest

from teukhos.adapters.cli import CLIAdapter
from teukhos.config import ArgConfig, ArgType, CLIAdapterConfig


@pytest.fixture
def echo_adapter():
    cli_config = CLIAdapterConfig(command="echo")
    args = [
        ArgConfig(name="message", type=ArgType.string, required=True, positional=True),
    ]
    return CLIAdapter(cli_config, args)


@pytest.fixture
def git_log_adapter():
    import pathlib as _pl
    _repo = str(_pl.Path(__file__).parent.parent)
    cli_config = CLIAdapterConfig(command="git", subcommand=["log", "--oneline"], working_dir=_repo)
    args = [
        ArgConfig(name="count", type=ArgType.integer, flag="-n", default=5),
    ]
    return CLIAdapter(cli_config, args)


@pytest.mark.asyncio
async def test_echo_basic(echo_adapter):
    result = await echo_adapter.execute(message="hello world")
    assert result.exit_code == 0
    assert result.stdout.strip() == "hello world"


@pytest.mark.asyncio
async def test_echo_empty(echo_adapter):
    result = await echo_adapter.execute(message="")
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_git_log(git_log_adapter):
    result = await git_log_adapter.execute(count=5)
    if result.exit_code == 128:
        import pytest as _p; _p.skip("No git history in this environment")
    assert result.exit_code == 0
    lines = [ln for ln in result.stdout.strip().split("\n") if ln]
    assert len(lines) <= 5


@pytest.mark.asyncio
async def test_timeout():
    cli_config = CLIAdapterConfig(command="sleep", timeout_seconds=1)
    args = [ArgConfig(name="seconds", type=ArgType.string, positional=True, required=True)]
    adapter = CLIAdapter(cli_config, args)
    result = await adapter.execute(seconds="10")
    assert result.exit_code == -1
    assert "timed out" in result.stderr


@pytest.mark.asyncio
async def test_nonexistent_command():
    cli_config = CLIAdapterConfig(command="nonexistent_binary_xyz")
    adapter = CLIAdapter(cli_config, [])
    warning = adapter.check_binary()
    assert warning is not None
    assert "not found" in warning


@pytest.mark.asyncio
async def test_exit_code():
    cli_config = CLIAdapterConfig(command="bash", subcommand=["-c"])
    args = [ArgConfig(name="cmd", type=ArgType.string, positional=True, required=True)]
    adapter = CLIAdapter(cli_config, args)
    result = await adapter.execute(cmd="exit 42")
    assert result.exit_code == 42


@pytest.mark.asyncio
async def test_boolean_flag():
    cli_config = CLIAdapterConfig(command="git", subcommand=["branch"])
    args = [ArgConfig(name="all", type=ArgType.boolean, flag="--all")]
    adapter = CLIAdapter(cli_config, args)
    cmd = adapter._build_command(all=True)
    assert "--all" in cmd
    cmd2 = adapter._build_command(all=False)
    assert "--all" not in cmd2


@pytest.mark.asyncio
async def test_json_output():
    cli_config = CLIAdapterConfig(command="echo")
    args = [ArgConfig(name="data", type=ArgType.string, positional=True, required=True)]
    adapter = CLIAdapter(cli_config, args)
    result = await adapter.execute(data='{"name": "test", "count": 42}')
    assert result.exit_code == 0
    assert "test" in result.stdout
