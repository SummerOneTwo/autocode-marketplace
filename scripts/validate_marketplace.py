"""Validate the committed multi-host AutoCode marketplace layout.

This check is intentionally dependency-free. The AutoCode source repository
owns bundle generation; this repository verifies that the committed catalog
and all host bundles (Claude Code / Codex, DeepSeek Harness, Antigravity)
are complete, version-synchronized, and self-described.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / ".agents" / "plugins" / "marketplace.json"
CLAUDE_CATALOG = ROOT / ".claude-plugin" / "marketplace.json"
BUNDLE = ROOT / "plugins" / "autocode"
DSH_BUNDLE = ROOT / "plugins" / "autocode-dsh"
AGY_BUNDLE = ROOT / "plugins" / "autocode-agy"


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


def require_path(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"{path.relative_to(ROOT)}: required path is missing")


def validate() -> list[str]:
    errors: list[str] = []
    catalog = load_object(CATALOG, errors)
    claude_catalog = load_object(CLAUDE_CATALOG, errors)
    codex_manifest = load_object(BUNDLE / ".codex-plugin" / "plugin.json", errors)
    claude_manifest = load_object(BUNDLE / ".claude-plugin" / "plugin.json", errors)
    release = load_object(BUNDLE / ".autocode-release.json", errors)
    dsh_manifest = load_object(DSH_BUNDLE / ".dsh-plugin" / "package.json", errors)
    dsh_release = load_object(DSH_BUNDLE / ".autocode-release.json", errors)
    agy_manifest = load_object(AGY_BUNDLE / "plugin.json", errors)
    agy_release = load_object(AGY_BUNDLE / ".autocode-release.json", errors)
    if any(
        item is None
        for item in (
            catalog,
            claude_catalog,
            codex_manifest,
            claude_manifest,
            release,
            dsh_manifest,
            dsh_release,
            agy_manifest,
            agy_release,
        )
    ):
        return errors

    assert catalog is not None
    assert claude_catalog is not None
    assert codex_manifest is not None
    assert claude_manifest is not None
    assert release is not None
    assert dsh_manifest is not None
    assert dsh_release is not None
    assert agy_manifest is not None
    assert agy_release is not None

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

    if require_string(claude_catalog.get("name"), "claude_catalog.name", errors) != "autocode-marketplace":
        errors.append("claude_catalog.name: expected 'autocode-marketplace'")

    # Validate Claude Code + Codex marketplace bundle
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

    # Validate DeepSeek Harness (dsh) bundle
    dsh_version = require_string(dsh_manifest.get("version"), "DSH package.json version", errors)
    dsh_release_version = require_string(dsh_release.get("version"), "DSH release.version", errors)
    if dsh_version != release_version or dsh_release_version != release_version:
        errors.append(
            f"DSH bundle version mismatch: package={dsh_version}, release={dsh_release_version}, expected={release_version}"
        )
    if not isinstance(dsh_release.get("source_fingerprint"), dict) or ".dsh-plugin" not in dsh_release["source_fingerprint"]:
        errors.append("DSH release.source_fingerprint: missing '.dsh-plugin' entry")
    require_path(DSH_BUNDLE / ".dsh-plugin" / "cordis.patch.yml", errors)
    require_path(DSH_BUNDLE / ".dsh-plugin" / "index.js", errors)
    require_path(DSH_BUNDLE / "skills", errors)
    require_path(DSH_BUNDLE / "src" / "autocode_mcp", errors)

    # Validate Antigravity (agy) bundle
    if require_string(agy_manifest.get("name"), "Antigravity plugin.json name", errors) != "autocode":
        errors.append("Antigravity plugin.json name must be 'autocode'")
    agy_version = require_string(agy_manifest.get("version"), "Antigravity plugin.json version", errors)
    agy_release_version = require_string(agy_release.get("version"), "Antigravity release.version", errors)
    if agy_version != release_version or agy_release_version != release_version:
        errors.append(
            f"Antigravity bundle version mismatch: plugin={agy_version}, release={agy_release_version}, expected={release_version}"
        )
    if not isinstance(agy_release.get("source_fingerprint"), dict) or "plugin.json" not in agy_release["source_fingerprint"]:
        errors.append("Antigravity release.source_fingerprint: missing 'plugin.json' entry")
    require_path(AGY_BUNDLE / "mcp_config.json", errors)
    require_path(AGY_BUNDLE / "rules" / "AGENTS.md", errors)
    require_path(AGY_BUNDLE / "agents", errors)
    require_path(AGY_BUNDLE / "skills", errors)
    require_path(AGY_BUNDLE / "src" / "autocode_mcp", errors)

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Marketplace layout is valid (all 3 host bundles synced): {ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
