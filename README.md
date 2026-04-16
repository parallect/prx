# prx

`.prx` format toolkit and [prxhub](https://prxhub.com) CLI.

Read, validate, diff, sign, merge, and publish `.prx` research bundles — the open archive format produced by [Parallect](https://github.com/parallect/parallect).

## Install

```bash
pip install prx
# or
uv pip install prx
```

For the interactive TUI browser:

```bash
pip install 'prx[tui]'
```

## Quick Start

```bash
# Read a bundle
prx read results.prx

# Validate bundle structure
prx validate results.prx

# Verify cryptographic attestation
prx verify results.prx

# Diff two bundles
prx diff a.prx b.prx

# Export to markdown / JSON
prx export results.prx --format markdown

# Merge bundles
prx merge a.prx b.prx -o combined.prx

# Open the TUI browser
prx open
```

## prxhub Commands

### First-time setup

```bash
# 1. Log in (opens a browser for device-code approval)
prx login

# 2. (Optional but recommended) generate a signing key and register it
prx keys generate
prx keys register

# 3. Publish
prx publish results.prx
```

`prx login` uses a device-code OAuth flow against prxhub: it prints a short
user code, opens your browser, and polls until you approve. The resulting
bearer token is stored at `~/.config/prx/auth.json` (chmod 0600) and is used
automatically for every subsequent authenticated command. Use
`prx login --api-url https://your-prxhub.example.com` for self-hosted
instances and `prx logout` / `prx whoami` to manage the session.

### Authentication model

All write operations against prxhub require a bearer token from `prx login`.
Read-only operations (`search`, `clone` of a public bundle, `get` metadata)
work without logging in.

Advanced users can also register an Ed25519 public key
(`prx keys register`) so bundles are additionally signature-verified on the
server. The signing key lives in the same directory the `parallect` CLI uses
(`~/.config/parallect/keys/`) so a bundle produced by parallect can be
published by prx without any migration step.

### Commands

```bash
# Session
prx login
prx logout
prx whoami

# Bundles
prx publish results.prx
prx search "quantum computing"
prx clone owner/repo-name

# Social
prx fork owner/repo-name
prx star owner/repo-name
prx push results.prx --repo my-research --branch main
```

## Repository Management

```bash
prx repo create my-research --description "..."
prx repo list
prx branch list owner/repo-name
prx branch create owner/repo-name feature-branch
prx mr create owner/repo-name --source feature --target main
```

## Key Management

Keys live in `~/.config/parallect/keys/` — shared with the parallect CLI.

```bash
# Generate a signing keypair (Ed25519)
prx keys generate

# List local keys
prx keys list

# Register your public key on prxhub (requires `prx login`)
prx keys register

# Revoke a registered public key
prx keys revoke prx_pub_<id>
```

## Configuration

```bash
prx config
```

Stores settings in `~/.config/prx/config.toml`:

- **prxhub API key** — for publishing and hub operations
- **Default visibility** — public, unlisted, or private
- **Signing identity** — name or email for bundle attestation

## Documentation

- [Format Guide](docs/FORMAT.md) — .prx bundle structure and usage
- [TUI Guide](docs/TUI-GUIDE.md) — Terminal UI screens and shortcuts
- [prxhub Guide](docs/PRXHUB.md) — Publishing and hub integration

## Development

```bash
git clone https://github.com/parallect/prx.git
cd prx
uv sync --group dev
uv run pytest tests/ -x -q
```

## License

MIT
