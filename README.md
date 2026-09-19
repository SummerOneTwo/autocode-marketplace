# AutoCode Marketplace

Claude Code and Codex marketplace for AutoCode distribution.

This repository is configured for remote HTTPS git installation. The default plugin source is `https://github.com/SZTU-ACM/AutoCode.git`.

The Codex catalog is kept in `.agents/plugins/marketplace.json` and points to the
versioned local bundle under `plugins/autocode/`. Regenerate that bundle from the
AutoCode source repository with `scripts/build_plugin_bundle.py` before publishing.
The dependency-free `scripts/validate_marketplace.py` checks the committed catalog,
manifests, and provenance metadata in this repository.

## Included Plugins

- `autocode` from `https://github.com/SZTU-ACM/AutoCode.git`

## Add to Claude Code

```bash
claude plugin marketplace add ./autocode-marketplace
```

Or from the parent directory:

```bash
claude plugin marketplace add c:/userProgram/program/autocode-marketplace
```

After adding the marketplace, install the plugin:

```bash
claude plugin install autocode@autocode-marketplace
```

## Add to Codex

From a local checkout, add this repository as a Codex marketplace and install the
bundle:

```bash
codex plugin marketplace add ./autocode-marketplace
codex plugin add autocode@autocode-marketplace
```

For a remote checkout, replace the path with the published marketplace URL. The
Codex catalog must be committed together with `plugins/autocode/`.

## Claude Remote Mode

The marketplace installs plugins from remote HTTPS git sources. For `autocode`, that means the plugin content must be pushed to `https://github.com/SZTU-ACM/AutoCode.git` before marketplace installs can consume the latest version.

Codex installs the committed bundle from this repository. Keeping the bundle and
its `.autocode-release.json` provenance file in sync is required before pushing.

## Local Testing

For local testing only, you can temporarily replace the GitHub source in `.claude-plugin/marketplace.json` with a local plugin path and run validation or installation against a local checkout. That local override should not be committed as the default marketplace mode.

## Validate

```bash
claude plugin validate .
python3 scripts/validate_marketplace.py
uv run python /root/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/autocode
```

## Switch To GitHub Distribution Later

The current committed mode is already HTTPS git-based. A plugin entry uses this structure:

```json
{
  "name": "autocode",
  "source": {
    "source": "url",
    "url": "https://github.com/SZTU-ACM/AutoCode.git"
  }
}
```
