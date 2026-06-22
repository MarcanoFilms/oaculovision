# OracleVision v2 — Architecture

> Sovereign UI/Dashboard for Bitcoin Knots operators.
> Philosophy: **Don't Trust, Verify** — all data from your own node.

## Overview

OracleVision v2 evolves from a single-page dashboard into a **multi-screen, keyboard-driven TUI** with clean separation between analysis, node interaction, and presentation. The goal is a daily-use tool for serious Knots operators running BIP-110 policies and DATUM mining.

```
┌─────────────────────────────────────────────────────────────────┐
│                         ui/  (Textual)                          │
│  screens · widgets · navigation · confirm dialogs               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ reads models, triggers actions
┌───────────────────────────▼─────────────────────────────────────┐
│                    services/  (orchestration)                    │
│  TemplateService · PolicyService · AlertAggregator               │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
┌───────────────▼──────────────┐  ┌──────────▼────────────────────┐
│       analysis/              │  │         node/                │
│  BIP-110 · spam · categorize │  │  client (read) · control     │
│  policies/ (simulation)      │  │  (write, gated)              │
└──────────────────────────────┘  └──────────┬────────────────────┘
                                             │
                              ┌──────────────▼────────────────────┐
                              │  data/  (external integrations)   │
                              │  DATUM API · Ocean API            │
                              └───────────────────────────────────┘
```

## Layer Responsibilities

### `analysis/` — Pure, testable logic

No I/O. Takes transaction/block dicts and returns structured results.

| Module | Purpose |
|--------|---------|
| `bip110.py` | Per-tx and per-block BIP-110 violation detection |
| `spam_score.py` | Block spam scoring and status classification |
| `mempool_compose.py` | Template tx categorization (economic, spam, etc.) |
| `script_parser.py` | Low-level witness/script parsing |
| `policies/` | Policy models, Knots policy parsing, simulation engine |

**Design rule:** Community contributors can add new detectors by extending `analyze_transaction()` flags or registering new policy rules — no UI changes required.

### `node/` — Verified node interaction

| Module | Purpose |
|--------|---------|
| `client.py` | Read-only `bitcoin-cli` wrapper (`NodeClient`) |
| `security.py` | Path/method validation (command injection prevention) |
| `control/actions.py` | Typed control action definitions |
| `control/gate.py` | Read-only mode check + confirmation requirement |

**Design rule:** Every write RPC goes through `ControlGate`. The UI never calls `bitcoin-cli` write methods directly.

### `data/` — External (non-node) data sources

| Module | Purpose |
|--------|---------|
| `datum.py` | DATUM gateway API |
| `ocean.py` | Ocean pool public API |

These are optional integrations — the tool works with node-only data.

### `services/` — Orchestration & caching

| Service | Purpose |
|---------|---------|
| `TemplateService` | Shared GBT fetch + composition cache |
| `PolicyService` | Knots policy snapshot + simulation orchestration |

### `ui/` — Textual presentation

| Module | Purpose |
|--------|---------|
| `app.py` | Main `SovereignApp` with sidebar navigation |
| `navigation.py` | Screen registry, keybindings |
| `screens/` | One screen per major section |
| `widgets/` | Reusable UI components (sidebar, confirm modal) |

Legacy widgets in `oraculovision/widgets/` remain during migration; dashboard screen composes them.

## Screen Map

| Screen | Key | Status | Description |
|--------|-----|--------|-------------|
| Dashboard | `1` | MVP (existing) | Overview: node, BIP-110, DATUM, charts |
| Policies | `2` | **MVP (v2)** | Knots policies + simulation |
| Mempool Glass | `3` | MVP (enhanced) | Full GBT analysis + tx table |
| Block Explorer | `4` | v1 | Search blocks by height/hash |
| Tx Inspector | `5` | v1 | Deep tx analysis |
| Spam & Health | `6` | v1 | Historical trends |
| Mining (DATUM) | `7` | MVP (existing) | Full-screen mining panel |
| Node Control | `8` | v1 (gated) | Peer/policy control actions |

Global: `r` refresh · `t` template · `u` utxo · `?` help · `q` quit

## Control Action Safety Model

```
User triggers action
        │
        ▼
┌───────────────────┐
│ config.control    │── read_only=true ──► Block with message
│ .read_only?       │
└────────┬──────────┘
         │ false
         ▼
┌───────────────────┐
│ ControlAction     │── builds confirmation text
│ .describe()       │
└────────┬──────────┘
         ▼
┌───────────────────┐
│ ConfirmModal      │── user must press Y
└────────┬──────────┘
         │ confirmed
         ▼
┌───────────────────┐
│ ControlGate       │── executes via NodeClient.call_write()
│ .execute()        │
└───────────────────┘
```

Allowed control actions (v1 scope):

- `disconnect_peer` — `disconnectnode`
- `ban_peer` — `setban` (subnet, duration)
- `clear_ban` — `clearbanned`
- `set_mempool_limit` — `setmempoollimit` (with warning)

Dangerous actions (restart, reindex, wallet) are **explicitly excluded**.

## Configuration

TOML + environment variables (unchanged precedence):

1. `ORACULOVISION_CONFIG`
2. `~/.config/oraculovision/config.toml`
3. Project `config.toml`

New `[control]` section:

```toml
[control]
read_only = true   # default: safe mode, no write RPCs
```

## Phased Roadmap

### Phase 0 — Foundation (current sprint)

- [x] Architecture document
- [x] `node/` layer with security + control gate
- [x] `analysis/policies/` simulation engine
- [x] Multi-screen navigation (`ui/`)
- [x] Policies screen (live Knots info + template simulation)
- [x] Enhanced Mempool Glass screen

### Phase 1 — MVP (v2.0)

- Dashboard as dedicated screen with alert aggregation
- Block Explorer (height/hash search, spam detail modal)
- Transaction Inspector (mempool + confirmed)
- Migrate all widgets into `ui/screens/`
- Unit tests for `analysis/` and `policies/`
- Read-only mode default in config

### Phase 2 — v1.0

- Spam & Chain Health (historical block DB, worst blocks)
- Node Control screen (peer ban/disconnect with confirm modal)
- Policy adjustment preview (show impact of stricter `bitcoin.conf` options)
- Mempool Glass: filterable tx table, per-tx drill-down
- Config hot-reload notification

### Phase 3 — v2.1 (complete)

- [x] Local block index cache for fast historical queries (SQLite `data/block_index.py`)
- [x] Custom detector plugin system (`analysis/detectors/*.py`)
- [x] Mining template builder (DATUM job inspection via `/` + `/coinbaser`)
- [x] Remote node profiles (local / RPC / SSH transport; press `p` to cycle)
- [x] Export reports (JSON/CSV) for audit trails (press `e`)

### Phase 4 — v2.2 (complete)

- [x] Transaction flow analysis (`analysis/tx_flow.py`) — inputs/outputs, amounts, fees
- [x] Address UTXO lookup (`services/address_service.py`, `scantxoutset`)
- [x] Tx & Address Inspector dual-mode (screen `5`)
- [x] Pruned-node UX: status bar badge, health scan clamp, partial flow display
- [x] Dashboard BIP-110 uses shared `BlockService` + persistent cache

## Module Migration Plan

| Current | Target | Action |
|---------|--------|--------|
| `data/bitcoin.py` | `node/client.py` | Refactor; keep re-export shim |
| `widgets/*` | `ui/screens/*` + `ui/widgets/*` | Gradual move |
| `app.py` | `ui/app.py` | New navigation shell |
| `analysis/*` | `analysis/*` | Keep; extend policies |
| — | `node/control/` | New |
| — | `analysis/policies/` | New |

## Testing Strategy

```
tests/
  analysis/
    test_bip110.py
    test_policies_simulator.py
  node/
    test_security.py
    test_control_gate.py
```

Analysis tests use fixture transactions (no node required).
Integration tests optional with regtest node.

## Contributing

1. **New spam detector:** Add flag in `analysis/bip110.py` or new file in `analysis/detectors/`
2. **New screen:** Register in `ui/navigation.py`, create `ui/screens/your_screen.py`
3. **New control action:** Add to `node/control/actions.py`, wire confirm modal in UI
4. **Never** add write RPC calls outside `node/control/`