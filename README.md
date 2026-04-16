# prx

[![PyPI version](https://img.shields.io/pypi/v/prx-cli.svg)](https://pypi.org/project/prx-cli/)
[![Python](https://img.shields.io/pypi/pyversions/prx-cli.svg)](https://pypi.org/project/prx-cli/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/parallect/prx/actions/workflows/ci.yml/badge.svg)](https://github.com/parallect/prx/actions/workflows/ci.yml)

**Toolkit and hub CLI for the [Portable Research eXchange (`.prx`)](https://github.com/parallect/prx-spec) format.**

PRX is an open format for packaging AI-generated research so it can be shared, verified, and attributed back to the providers and sources behind every claim — privately within a team or publicly to the world. `prx` is the toolkit for working with those archives: read, validate, diff, merge, sign, and publish.

It pairs naturally with [`parallect`](https://github.com/parallect/parallect) (which produces `.prx` bundles from multi-provider research runs) and [prxhub](https://prxhub.com) (the public registry for sharing them).

```bash
$ prx read results.prx
$ prx publish results.prx --collection ai-safety
$ prx open                   # Terminal UI browser
```

## Install

```bash
pip install prx-cli
```

The CLI is installed as `prx` (the PyPI distribution is `prx-cli` because
`prx` was already taken).

For the interactive TUI browser:

```bash
pip install 'prx-cli[tui]'
```

Requires Python 3.10+.

## What you can do

- **Read + validate** any `.prx` bundle — L0/L1/L2 structural checks
- **Verify attestations** — Ed25519 JWS signatures and per-file attestations
- **Diff and merge** bundles — compute consensus + disagreement between research runs
- **Publish to prxhub** — share, tag, collection-assign, fork, star
- **Manage signing keys** — generate, list, register with the hub, revoke
- **Browse visually** — a terminal UI for exploring bundle contents (with `[tui]` extra)

## Quick start

### Working with local bundles

```bash
# Inspect the contents
prx read results.prx

# Structural validation (L0/L1/L2)
prx validate results.prx

# Verify Ed25519 attestations
prx verify results.prx

# Diff two bundles — shows added/removed claims and provider drift
prx diff a.prx b.prx

# Merge bundles — combines providers, claims, and sources
prx merge a.prx b.prx -o combined.prx

# Export for sharing
prx export results.prx --format markdown
```

### Publishing to prxhub

```bash
# One-time setup — interactive config for API key and signing identity
prx config

# Generate a signing keypair (stored in ~/.config/prx/)
prx keys generate

# Publish a bundle
prx publish results.prx --visibility public --tags "consensus,distributed-systems"

# Publish directly into a collection (created if missing)
prx publish results.prx --collection ai-safety

# Search the hub
prx search "quantum computing"

# Clone someone else's bundle
prx clone alice/quantum-consensus
```

### Repositories, branches, merge requests

prxhub supports Git-style collaboration on research. See [`docs/PRXHUB.md`](docs/PRXHUB.md) for the full workflow.

```bash
prx repo create my-research --description "Ongoing literature review"
prx branch create alice/my-research experiment
prx push results.prx --repo my-research --branch experiment
prx mr create alice/my-research --source experiment --target main
```

### Terminal UI

```bash
prx open
```

Browse installed bundles, read synthesis + per-provider reports, and search hub content without leaving the terminal. See [`docs/TUI-GUIDE.md`](docs/TUI-GUIDE.md).

## Commands

### Bundle tools (offline)

| Command | Purpose |
|---|---|
| `prx read <bundle>` | Display bundle contents (query, providers, synthesis) |
| `prx validate <bundle>` | Structural validation (L0/L1/L2) |
| `prx verify <bundle>` | Verify cryptographic attestations |
| `prx diff <a> <b>` | Compare two bundles |
| `prx merge <a> <b> -o <out>` | Merge providers, claims, sources |
| `prx export <bundle>` | Export to markdown / JSON |
| `prx list <dir>` | List bundles in a directory |
| `prx open` | Terminal UI browser (requires `[tui]`) |

### Hub commands

| Command | Purpose |
|---|---|
| `prx config` | Interactive configuration |
| `prx publish <bundle>` | Upload to prxhub |
| `prx search <query>` | Search published bundles |
| `prx clone <owner/repo>` | Download a published bundle |
| `prx fork <owner/repo>` | Fork for follow-on research |
| `prx star <owner/repo>` | Star a bundle |
| `prx repo <subcmd>` | Repository management |
| `prx branch <subcmd>` | Branch management |
| `prx push <bundle>` | Push to a repo branch |
| `prx mr <subcmd>` | Merge request management |

### Key management

| Command | Purpose |
|---|---|
| `prx keys generate` | Generate an Ed25519 signing keypair |
| `prx keys list` | List local keys |
| `prx keys register` | Register a public key with prxhub |
| `prx keys revoke` | Revoke a registered key |

Run `prx <command> --help` for full flags.

## Configuration

`prx config` writes to `~/.config/prx/config.toml`:

- **prxhub API key** — for publishing and hub operations (get one at [prxhub.com](https://prxhub.com))
- **Default visibility** — `public`, `unlisted`, or `private`
- **Signing identity** — name or email embedded in bundle attestations

## Documentation

- [Format Guide](docs/FORMAT.md) — `.prx` bundle structure
- [TUI Guide](docs/TUI-GUIDE.md) — terminal UI reference
- [prxhub Guide](docs/PRXHUB.md) — publishing, collections, repos, merge requests

## Development

```bash
git clone https://github.com/parallect/prx.git
cd prx
uv sync --group dev
uv run pytest tests/ -x -q
uv run ruff check src/ tests/
```

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). For security reports, email `security@parallect.ai`.

## License

MIT — see [LICENSE](LICENSE).

---

Built by [SecureCoders](https://securecoders.com). A hosted managed version is available at [parallect.ai](https://parallect.ai) — same `.prx` output, with a multi-provider research API, billing, and a web dashboard.
