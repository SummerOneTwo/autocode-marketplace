# AutoCode Marketplace

Official multi-host plugin distribution repository for [SZTU-ACM/AutoCode](https://github.com/SZTU-ACM/AutoCode).

> Looking for product features, standalone CLI usage, or reference docs? Visit the [main AutoCode repository](https://github.com/SZTU-ACM/AutoCode).

This repository distributes synchronized plugin bundles for all four supported AI clients:

| Client | Path / Catalog | Notes |
|--------|----------------|-------|
| **Claude Code** | `.claude-plugin/marketplace.json` | Remote HTTPS git catalog pointing to `https://github.com/SZTU-ACM/AutoCode.git` |
| **Codex** | `.agents/plugins/marketplace.json` → `plugins/autocode/` | Pre-built local plugin bundle synced from AutoCode |
| **DeepSeek Harness (`dsh`)** | `plugins/autocode-dsh/` | Self-contained DSH plugin bundle (`.dsh-plugin/`, `skills/`, `rules/`, `src/`) |
| **Antigravity (`agy`)** | `plugins/autocode-agy/` | Native Antigravity plugin bundle (`plugin.json`, `mcp_config.json`, `rules/AGENTS.md`, `agents/`, `skills/`, `src/`) |

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

Run from the `SZTU-ACM/AutoCode` source repository when syncing updates:

```bash
uv run python scripts/build_plugin_bundle.py --target marketplace --output ../autocode-marketplace/plugins/autocode
uv run python scripts/build_plugin_bundle.py --target dsh --output ../autocode-marketplace/plugins/autocode-dsh
uv run python scripts/build_plugin_bundle.py --target agy --output ../autocode-marketplace/plugins/autocode-agy
```

## Validate

```bash
python3 scripts/validate_marketplace.py
```
