"""Installer for OpenAI Codex CLI."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from teukhos.installers.base import BaseInstaller, InstallScope


class CodexInstaller(BaseInstaller):
    name = "Codex"
    slug = "codex"
    supported_scopes = [InstallScope.global_, InstallScope.project]

    _config_path_override: dict[InstallScope, Path] | None = None

    def detect(self) -> bool:
        return self.config_path(InstallScope.global_).parent.exists()

    def config_path(self, scope: InstallScope) -> Path:
        if self._config_path_override and scope in self._config_path_override:
            return self._config_path_override[scope]
        effective = self._effective_scope(scope)
        if effective == InstallScope.project:
            return self.cwd / ".codex" / "config.toml"
        return Path.home() / ".codex" / "config.toml"

    def install_stdio(self, server_name: str, teukhos_config_path: Path,
                      scope: InstallScope = InstallScope.global_) -> None:
        teukhos_bin = shutil.which("teukhos") or "teukhos"
        effective = self._effective_scope(scope)
        path = self.config_path(effective)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing section if present
        self._remove_section(path, server_name)

        section = (
            f'\n[mcp_servers.{server_name}]\n'
            f'type = "stdio"\n'
            f'command = "{teukhos_bin}"\n'
            f'args = ["serve", "{teukhos_config_path}"]\n'
        )
        with open(path, "a", encoding="utf-8") as f:
            f.write(section)

    def install_http(self, server_name: str, url: str, api_key: str | None,
                     scope: InstallScope = InstallScope.global_) -> None:
        effective = self._effective_scope(scope)
        path = self.config_path(effective)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing section if present
        self._remove_section(path, server_name)

        lines = [
            f'\n[mcp_servers.{server_name}]',
            f'type = "url"',
            f'url = "{url}"',
        ]
        if api_key:
            if api_key.startswith("env:"):
                env_var = api_key[4:]
                lines.append('')
                lines.append(f'[mcp_servers.{server_name}.headers]')
                lines.append(f'Authorization = "Bearer ${{{env_var}}}"')
            else:
                lines.append('')
                lines.append(f'[mcp_servers.{server_name}.headers]')
                lines.append(f'Authorization = "Bearer {api_key}"')

        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def uninstall(self, server_name: str,
                  scope: InstallScope = InstallScope.global_) -> None:
        effective = self._effective_scope(scope)
        path = self.config_path(effective)
        self._remove_section(path, server_name)

    def _remove_section(self, path: Path, server_name: str) -> None:
        """Remove a [mcp_servers.<name>] section and its subsections from a TOML file."""
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        # Remove the main section and any sub-sections (like .headers)
        pattern = rf'\n?\[mcp_servers\.{re.escape(server_name)}(?:\.[^\]]+)?\]\n(?:[^\[]*(?:\n|$))*'
        new_text = re.sub(pattern, '\n', text)
        # Clean up multiple blank lines
        new_text = re.sub(r'\n{3,}', '\n\n', new_text).strip()
        if new_text:
            new_text += '\n'
        path.write_text(new_text, encoding="utf-8")
