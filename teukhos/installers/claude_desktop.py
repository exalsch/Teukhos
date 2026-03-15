"""Installer for Claude Desktop."""

from __future__ import annotations

import platform
from pathlib import Path

from teukhos.installers.base import InstallScope, JsonMcpInstaller


class ClaudeDesktopInstaller(JsonMcpInstaller):
    name = "Claude Desktop"
    slug = "claude-desktop"
    supported_scopes = [InstallScope.global_]
    supports_env_substitution = False

    def config_path(self, scope: InstallScope) -> Path:
        if self._config_path_override and scope in self._config_path_override:
            return self._config_path_override[scope]
        system = platform.system()
        if system == "Darwin":
            return (
                Path.home() / "Library" / "Application Support"
                / "Claude" / "claude_desktop_config.json"
            )
        elif system == "Windows":
            return (
                Path.home() / "AppData" / "Roaming"
                / "Claude" / "claude_desktop_config.json"
            )
        return Path.home() / ".config" / "claude" / "claude_desktop_config.json"
