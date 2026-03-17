"""Installer for Cline (VS Code extension)."""
from __future__ import annotations
import platform
from pathlib import Path
from teukhos.installers.base import InstallScope, JsonMcpInstaller

class ClineInstaller(JsonMcpInstaller):
    name = "Cline"
    slug = "cline"
    supported_scopes = [InstallScope.global_]

    def config_path(self, scope: InstallScope) -> Path:
        if self._config_path_override and scope in self._config_path_override:
            return self._config_path_override[scope]
        system = platform.system()
        if system == "Windows":
            return (Path.home() / "AppData" / "Roaming" / "Code" / "User"
                    / "globalStorage" / "saoudrizwan.claude-dev" / "settings"
                    / "cline_mcp_settings.json")
        elif system == "Darwin":
            return (Path.home() / "Library" / "Application Support" / "Code" / "User"
                    / "globalStorage" / "saoudrizwan.claude-dev" / "settings"
                    / "cline_mcp_settings.json")
        else:
            return (Path.home() / ".config" / "Code" / "User"
                    / "globalStorage" / "saoudrizwan.claude-dev" / "settings"
                    / "cline_mcp_settings.json")
