# prxhub Integration Guide

Publish, browse, and manage research bundles on prxhub.com.

## Setup

```bash
pip install prx
```

Configure your hub credentials:

```bash
prx config set hub_url https://prxhub.com
prx config set hub_api_key par_live_...
```

Or via environment variables:

```bash
export PRX_HUB_URL=https://prxhub.com
export PRX_HUB_API_KEY=par_live_...
```

## Publishing Bundles

```bash
# Push a bundle to prxhub
prx push research.prx

# Push with tags
prx push research.prx --tags "quantum,physics"

# Push to a specific repo
prx push research.prx --repo my-research
```

## Key Management

Register your Ed25519 public key with prxhub for attestation verification:

```bash
# Generate a signing key (if you haven't already)
prx keys generate

# Register with prxhub
prx keys register

# List registered keys
prx keys list
```

## Browsing

```bash
# Search bundles on prxhub
prx search "quantum computing"

# Download a bundle
prx pull username/bundle-slug -o local.prx
```

## Repository Management

```bash
# Create a new repo
prx repo create my-research --description "My research collection"

# List your repos
prx repo list

# Create a branch
prx branch create my-research/experiment-1

# Create a merge request
prx mr create my-research/experiment-1 --title "Add new findings"
```

## Authentication

prx supports two authentication methods:

1. **API Key** — `par_live_*` keys for CLI and programmatic access
2. **Login with Parallect** — OAuth2 SSO via parallect.ai account (coming soon)

## Publishing Workflow

```
parallect research "query" -o bundle.prx    # Generate research
prx validate bundle.prx                      # Validate
prx push bundle.prx                          # Publish to hub
```

Your bundle will be visible at `prxhub.com/{username}/{slug}` with:

- Full synthesis rendering
- Per-provider report tabs
- Claims table
- Source registry
- Trust badges (attestation verification)
