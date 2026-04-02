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

```bash
# Configure API key and signing identity
prx config

# Publish a bundle
prx publish results.prx

# Search published bundles
prx search "quantum computing"

# Clone a bundle
prx clone owner/repo-name

# Fork, star, push
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

```bash
# Generate a signing keypair
prx keys generate

# Export public key
prx keys export
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
