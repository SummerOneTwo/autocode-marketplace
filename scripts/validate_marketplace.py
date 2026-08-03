"""Validate the committed Claude/Codex marketplace layout.

This check is intentionally dependency-free.  The AutoCode source repository
owns bundle generation; this repository only verifies that the committed
catalog points at a complete, self-described bundle.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / ".agents" / "plugins" / "marketplace.json"
BUNDLE = ROOT / "plugins" / "autocode"


def load_object(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: cannot read JSON ({exc})")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(ROOT)}: expected a JSON object")
        return None
    return value


def require_string(value: Any, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: expected a non-empty string")
        return None
    return value


def validate() -> list[str]:
    errors: list[str] = []
    catalog = load_object(CATALOG, errors)
    codex_manifest = load_object(BUNDLE / ".codex-plugin" / "plugin.json", errors)
    claude_manifest = load_object(BUNDLE / ".claude-plugin" / "plugin.json", errors)
    release = load_object(BUNDLE / ".autocode-release.json", errors)
    if catalog is None or codex_manifest is None or claude_manifest is None or release is None:
        return errors

    if require_string(catalog.get("name"), "catalog.name", errors) != "autocode-marketplace":
        errors.append("catalog.name: expected 'autocode-marketplace'")
    interface = catalog.get("interface")
    if not isinstance(interface, dict):
        errors.append("catalog.interface: expected an object")
    else:
        require_string(interface.get("displayName"), "catalog.interface.displayName", errors)

    plugins = catalog.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        errors.append("catalog.plugins: expected exactly one plugin entry")
    else:
        entry = plugins[0]
        if not isinstance(entry, dict):
            errors.append("catalog.plugins[0]: expected an object")
        else:
            if require_string(entry.get("name"), "catalog.plugins[0].name", errors) != "autocode":
                errors.append("catalog.plugins[0].name: expected 'autocode'")
            source = entry.get("source")
            if not isinstance(source, dict):
                errors.append("catalog.plugins[0].source: expected an object")
            else:
                if source.get("source") != "local":
                    errors.append("catalog.plugins[0].source.source: expected 'local'")
                if source.get("path") != "./plugins/autocode":
                    errors.append("catalog.plugins[0].source.path: expected './plugins/autocode'")
            policy = entry.get("policy")
            if not isinstance(policy, dict):
                errors.append("catalog.plugins[0].policy: expected an object")
            else:
                if policy.get("installation") not in {
                    "NOT_AVAILABLE",
                    "AVAILABLE",
                    "INSTALLED_BY_DEFAULT",
                }:
                    errors.append("catalog.plugins[0].policy.installation: invalid value")
                if policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
                    errors.append("catalog.plugins[0].policy.authentication: invalid value")
            require_string(entry.get("category"), "catalog.plugins[0].category", errors)

    codex_name = require_string(codex_manifest.get("name"), "Codex manifest name", errors)
    claude_name = require_string(claude_manifest.get("name"), "Claude manifest name", errors)
    if codex_name != "autocode" or claude_name != "autocode":
        errors.append("plugin manifests must both use the name 'autocode'")
    codex_version = require_string(codex_manifest.get("version"), "Codex manifest version", errors)
    claude_version = require_string(claude_manifest.get("version"), "Claude manifest version", errors)
    release_version = require_string(release.get("version"), "release.version", errors)
    if codex_version != claude_version or codex_version != release_version:
        errors.append("plugin manifest versions and release.version must match")
    if not isinstance(release.get("source_fingerprint"), dict) or not release["source_fingerprint"]:
        errors.append("release.source_fingerprint: expected a non-empty object")
    if codex_manifest.get("mcpServers") != "./.mcp.json":
        errors.append("Codex manifest must point at ./.mcp.json")
    if codex_manifest.get("skills") != "./skills/":
        errors.append("Codex manifest must point at ./skills/")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Marketplace layout is valid: {ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
