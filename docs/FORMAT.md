# prx Format Guide

## What is a .prx File?

A `.prx` file is a portable research bundle — a gzipped tar archive that packages an AI research session into a single, self-contained file.

Think of it like a `.docx` but for multi-provider AI research: query, reports, synthesis, claims, sources, and cryptographic signatures all in one file.

## Bundle Structure

```
bundle.prx (tar.gz)
├── manifest.json              # Bundle metadata
├── query.md                   # Research question
├── providers/
│   ├── perplexity.md          # Provider research reports
│   ├── gemini.md
│   ├── openai.md
│   └── citations/
│       ├── perplexity.json    # Per-provider citations
│       ├── gemini.json
│       └── openai.json
├── synthesis/
│   ├── report.md              # Unified synthesis
│   ├── claims.json            # Extracted claims
│   ├── meta.json              # Synthesis metadata
│   └── follow_ons.json        # Suggested follow-up queries
├── sources/
│   └── registry.json          # Deduplicated source registry
├── evidence/
│   ├── graph.json             # Evidence graph
│   └── clusters.json          # Evidence clusters
├── attestations/              # Cryptographic signatures
│   ├── bundle.researcher.*.sig.json
│   └── providers.perplexity.*.sig.json
└── plugins/                   # Plugin artifacts
```

## Working with Bundles

### Reading

```bash
# Open in terminal UI
prx open bundle.prx

# Quick info
prx info bundle.prx

# Extract to directory
prx extract bundle.prx -o output/
```

### Validation

```bash
# Level 0: Structure check (files exist, valid JSON)
prx validate bundle.prx

# Level 1: Schema validation
prx validate bundle.prx --level 1

# Level 2: Full semantic validation
prx validate bundle.prx --level 2
```

### Comparison

```bash
# Diff two bundles
prx diff bundle-a.prx bundle-b.prx
```

### Merging

```bash
# Merge multiple bundles on the same topic
prx merge bundle-a.prx bundle-b.prx -o merged.prx
```

## Manifest Fields

| Field | Type | Description |
|-------|------|-------------|
| `spec_version` | string | Format version (currently "1.0") |
| `id` | string | Unique bundle identifier (`prx_<hex>`) |
| `query` | string | Original research question |
| `created_at` | ISO 8601 | Creation timestamp |
| `producer` | object | `{name, version}` of generating tool |
| `providers_used` | string[] | Provider names that contributed |
| `has_synthesis` | bool | Whether synthesis was generated |
| `has_claims` | bool | Whether claims were extracted |
| `total_cost_usd` | float? | Total API cost |
| `total_duration_seconds` | float? | Wall-clock research time |
| `parent_bundle_id` | string? | For continuation chains |

## Attestation Types

| Type | Signer | What it Proves |
|------|--------|----------------|
| `provider_response` | `provider` | Provider generated this report |
| `synthesis` | `platform` | Platform produced this synthesis |
| `claim_extraction` | `platform` | Platform extracted these claims |
| `enhancement` | `platform` | Platform enhanced this bundle |
| `bundle` | `researcher` | Researcher vouches for this bundle |

## JSON Schemas

Schemas are published at `prxhub.com/schemas/v1/`:

- `manifest.json`
- `citations.json`
- `claims.json`
- `sources-registry.json`
- `evidence-graph.json`
- `evidence-clusters.json`
- `follow-ons.json`
- `provider-meta.json`
- `attestation.json`
- `continuations.json`
