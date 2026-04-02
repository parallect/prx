# Terminal UI Guide

The prx TUI provides an interactive terminal interface for browsing `.prx` research bundles.

## Installation

```bash
pip install "prx[tui]"
```

## Launching

```bash
# Open a specific bundle
prx open results.prx

# Browse all bundles in the current directory
prx open
```

## Screens

### Bundle Browser (`b`)

The default landing screen. Scans the current directory recursively for `.prx` files and displays:

- **File** — Relative path to the bundle
- **ID** — Bundle identifier
- **Query** — Research question (truncated)
- **Providers** — Providers that contributed
- **Created** — Creation date

### Report Viewer (`r`)

Side-by-side view with a provider list on the left and the full markdown report on the right.

- Click a provider name to view its report
- "Synthesis" entry shows the unified synthesis

### Claims Viewer (`c`)

DataTable showing all extracted claims:

- **#** — Claim number
- **Claim** — Claim text (truncated)
- **Supporting** — Providers that support this claim
- **Contradicting** — Providers that contradict it
- **Category** — Claim category

### Sources Viewer (`s`)

Source registry browser:

- **URL** — Source URL
- **Title** — Page title
- **Quality** — Quality tier (authoritative, reliable, mixed, unverified)
- **Providers** — Which providers cited this source
- **Citations** — Total citation count

### Diff Viewer (`d`)

Side-by-side comparison of two bundles showing differences in:

- Metadata (ID, query, creation date, producer)
- Providers (shared and unique)
- Synthesis presence
- Cost and duration
- Claims and sources counts
- Per-provider report lengths

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `b` | Bundle browser |
| `r` | Report viewer |
| `c` | Claims viewer |
| `s` | Sources viewer |
| `d` | Diff viewer |
