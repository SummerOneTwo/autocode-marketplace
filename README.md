# AutoCode Marketplace

Third-party Claude Code marketplace for private or personal plugin distribution.

This repository is configured for remote GitHub-based plugin installation. The default plugin source is `SummerOneTwo/AutoCode`.

## Included Plugins

- `autocode-mcp` from `SummerOneTwo/AutoCode`

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
claude plugin install autocode-mcp@autocode-marketplace
```

## Remote Mode

The marketplace installs plugins from remote GitHub sources. For `autocode-mcp`, that means the plugin content must be pushed to `SummerOneTwo/AutoCode` before marketplace installs can consume the latest version.

## Local Testing

For local testing only, you can temporarily replace the GitHub source in `.claude-plugin/marketplace.json` with a local plugin path and run validation or installation against a local checkout. That local override should not be committed as the default marketplace mode.

## Validate

```bash
claude plugin validate .
```

## Switch To GitHub Distribution Later

The current committed mode is already GitHub-based. A plugin entry uses this structure:

```json
{
  "name": "autocode-mcp",
  "source": {
    "source": "github",
    "repo": "SummerOneTwo/AutoCode"
  }
}
```
