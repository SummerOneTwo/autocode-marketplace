# AutoCode Marketplace

Official multi-host plugin distribution repository for [SZTU-ACM/AutoCode](https://github.com/SZTU-ACM/AutoCode).

> **Current Synchronized Release**: [`v4.0.0`](https://github.com/SZTU-ACM/AutoCode/releases/tag/v4.0.0) (22 MCP Tools + MCP 2026 Tasks/Apps/HTTP · 5 Agents · 11 Skills · Pluggable Sandboxes · 5 Languages · 5 OJ Exporters)

This repository distributes synchronized AutoCode plugin bundles for all four supported AI clients:

| Client | Path / Catalog | Notes |
|--------|----------------|-------|
| **Claude Code** | `.claude-plugin/marketplace.json` | Remote HTTPS git catalog pointing to `https://github.com/SZTU-ACM/AutoCode.git` |
| **Codex** | `.agents/plugins/marketplace.json` → `plugins/autocode/` | Versioned local bundle built from AutoCode (`v4.0.0`) |
| **DeepSeek Harness (`dsh`)** | `plugins/autocode-dsh/` | Self-contained DSH plugin bundle (`.dsh-plugin/`, `skills/`, `rules/`, `src/`) |
| **Antigravity (`agy`)** | `plugins/autocode-agy/` | Native Antigravity plugin bundle (`plugin.json`, `mcp_config.json`, `rules/AGENTS.md`, `agents/`, `skills/`, `src/`) |

## What's Included in v4.0.0

- **MCP 2026 Protocol & Interactive UI**: All 22 tools expose `ToolAnnotations`, inlined `outputSchema`/`structuredContent`, bounded async `MCP Tasks`, 3 zero-CDN `ui://autocode/*` MCP Apps (`complexity-plot`, `audit-dashboard`, `protocol-replay`), `stdio` default, and optional stateless Streamable HTTP (`--transport http`).
- **Red-Team Auditing, Coverage & Strong Mutation**: Dedicated `autocode-redteam-auditor` agent and `redteam-hacking` skill, built-in `jngen.h` + `testlib.h`, exact `expected_verdict` (`AC|WA|TLE|MLE|RE|PE`), `llvm-cov`/`gcov` branch coverage, `CounterexampleShrinker`, AST semantic mutation (`--extra ast`), multi-sanitizer UB probes, and `test_compactor`.
- **Pluggable Sandboxes & Formal Checks**: `--sandbox auto|none|bwrap|nsjail|isolate|apple_container`, optional Z3 SMT constraint verification + `constraints.h` (`--extra formal`), Orchid 4D ambiguity & local originality checks, and hardware performance counter empirical complexity analysis.
- **Multi-Language & 5-OJ Interop**: `cpp`, `python`, `pypy`, `rust`, and `java` execution with language multipliers; exports for Polygon, Hydro, QOJ, ICPC/Kattis, and IOI CMS; Polygon REST sync (`autocode_mcp.cli.polygon_sync`) and Typst PDF rendering (`autocode_mcp.cli.render_pdf`).

> **Optional Extras**: Install `tree-sitter-cpp` AST support and `z3-solver` SMT constraint support in the plugin's `uv` environment via `uv sync --all-extras` (or `--extra ast --extra formal`).

## Install by Client

### 1. Claude Code

```bash
claude plugin marketplace add https://github.com/SummerOneTwo/autocode-marketplace.git
claude plugin install autocode@autocode-marketplace
```

### 2. Codex

```bash
codex plugin marketplace add https://github.com/SummerOneTwo/autocode-marketplace.git
codex plugin add autocode@autocode-marketplace
```

### 3. DeepSeek Harness (`dsh`)

```bash
git clone https://github.com/SummerOneTwo/autocode-marketplace.git
dsh plugin add ./autocode-marketplace/plugins/autocode-dsh/.dsh-plugin
```

### 4. Antigravity (`agy`)

```bash
git clone https://github.com/SummerOneTwo/autocode-marketplace.git
mkdir -p ~/.gemini/config/plugins && rm -rf ~/.gemini/config/plugins/autocode
cp -R ./autocode-marketplace/plugins/autocode-agy ~/.gemini/config/plugins/autocode
```

## Regenerating Bundles from Source

Run from the `SZTU-ACM/AutoCode` source repository before publishing a new version:

```bash
uv run python scripts/build_plugin_bundle.py --target marketplace --output ../autocode-marketplace/plugins/autocode
uv run python scripts/build_plugin_bundle.py --target dsh --output ../autocode-marketplace/plugins/autocode-dsh
uv run python scripts/build_plugin_bundle.py --target agy --output ../autocode-marketplace/plugins/autocode-agy
```

## Validate

```bash
python3 scripts/validate_marketplace.py
```
