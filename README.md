# OraculoVision
<img width="1920" height="1056" alt="image" src="https://github.com/user-attachments/assets/31233dd5-727b-44ec-90f8-2bb2b4364287" />

Terminal dashboard (TUI) for sovereign operators running **Bitcoin Knots** with **BIP-110** enabled and **DATUM** for solo mining.

Philosophy: **Don't Trust, Verify**.

## Features

| Panel | Description |
|-------|-------------|
| **Node Status** | Sync, peers, mempool, UTXO set (manual refresh), alerts |
| **BIP-110 Detector** | Spam score, status, miner tags, navigable table |
| **Block Detail Modal** | Full per-block detail (Enter) |
| **DATUM Mining** | Gateway, workers, hashrate, shares |
| **Ocean Account** | Pool hashrate, TIDES, earnings, blocks found |
| **Mempool Glass** | **Real Block Template** composition (all GBT txs) |
| **Block Template** | Compact GBT summary + top 5 fee rates |
| **Live Metrics** | Mempool and peer charts |

## Requirements

- Python 3.11+
- [Bitcoin Knots](https://bitcoinknots.org/) with RPC available via `bitcoin-cli`
- (Optional) [DATUM Gateway](https://github.com/OCEAN-xyz/datum_gateway) for the mining panel
- (Optional) Ocean payout address for pool account stats (no API key required)

## Installation

### From the repository

```bash
git clone https://github.com/MarcanoFilms/oraculovision.git
cd oraculovision
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configuration

```bash
mkdir -p ~/.config/oraculovision
cp config.example.toml ~/.config/oraculovision/config.toml
# Edit the file for your environment
```

You can also place `config.toml` in the project root for local development.

### Run

```bash
oraculovision
# or
python main.py
```

### Global shortcut (optional)

```bash
./install-shortcut.sh
```

This creates `~/.local/bin/oraculovision` pointing at the project's virtual environment.

## Keyboard shortcuts

### Global

| Key | Action |
|-----|--------|
| `r` | Refresh all panels (light RPCs, cached template) |
| `t` | Refresh Block Template + Mempool Glass (full GBT) |
| `u` | Refresh UTXO set stats (slow RPC, ~2 min, background) |
| `o` | Enter or change Ocean payout address |
| `q` | Quit |
| `?` | Full help screen |
| `Tab` | Move focus between panels |

### BIP-110 Detector
<img width="968" height="599" alt="image" src="https://github.com/user-attachments/assets/509b9eac-7ccf-4b8c-8cb5-cb1c858b1625" />


| Key | Action |
|-----|--------|
| `↑` `↓` | Navigate block table |
| `Enter` | Open block detail modal |

### Block modal

<img width="1912" height="1031" alt="image" src="https://github.com/user-attachments/assets/81f9ee7e-d941-44a5-8b2a-21caac40cd9e" />

| Key | Action |
|-----|--------|
| `c` | Copy hash to clipboard |
| `Esc` | Close |

### Ocean address modal

| Key | Action |
|-----|--------|
| `Enter` | Apply address (empty clears session address) |
| `Esc` | Cancel without changes |

## Visual alerts

- **Red border** on Node Status — low peer count
- **Yellow border** on Node Status — congested mempool
- **Red border** on BIP-110 — high-spam tip block
- **Red border** on Mempool Glass — >30% spam weight
- **Top banner** — summary of active alerts

## Configuration

OraculoVision looks for configuration in this order:

1. `ORACULOVISION_CONFIG` environment variable
2. `~/.config/oraculovision/config.toml`
3. `config.toml` in the project root

See `config.example.toml` for all available options.

### Environment variables

| Variable | Description |
|----------|-------------|
| `BITCOIN_CLI` | Path to `bitcoin-cli` |
| `BITCOIN_DATADIR` | Node data directory |
| `DATUM_API_URL` | DATUM API (default `http://127.0.0.1:7152`) |
| `DATUM_CONFIG` | Path to DATUM gateway JSON config |
| `OCEAN_API_URL` | Ocean API base URL (default `https://api.ocean.xyz`) |
| `ORACULOVISION_CONFIG` | Path to `config.toml` |

### Ocean account

Set a default payout address in `config.toml`:

```toml
[ocean]
address = "bc1q..."
```

Or press **`o`** in the dashboard to enter or change the address for the current session (session override takes priority over config).

The **DATUM Mining** panel shows:

- **Hashrate** — your 60s / 5min hashrate vs pool, shares, and % of pool
- **TIDES window** — your share of the current TIDES window
- **Earnings & Payouts** — est. per day, unpaid balance, next block estimate, lifetime (30d)
- **Blocks earned (TIDES)** — pool blocks you earned from in the last 30 days
- **Blocks found by you** — blocks your workers actually solved (paginated Ocean API)
- **Workers hashing** — active workers with non-zero hashrate

Ocean stats are fetched from the public [Ocean API](https://api.ocean.xyz) and cached for 60 seconds. The blocks-found count uses a separate 5-minute cache to avoid hammering the API on every refresh.

## Performance

Auto-refresh is tuned to stay responsive on a live node:

| Resource | Auto-refresh | Manual |
|----------|--------------|--------|
| UTXO set (`gettxoutsetinfo`) | Skipped | `u` (background thread, ~2 min) |
| Block Template / Mempool Glass | 30s cache | `t` (full GBT fetch) |
| BIP-110 block table | Only when chain tip changes | `r` |
| Ocean blocks-found count | 5 min cache | `r` after cache expires |

Press **`r`** for a light refresh of sync, peers, mempool, DATUM, and Ocean hashrate. Use **`t`** and **`u`** only when you need heavy RPC data.

## Mempool Glass
<img width="901" height="368" alt="image" src="https://github.com/user-attachments/assets/b4e40f9a-1614-4047-b687-a853fed352d8" />

Analyzes the **current Block Template** (`getblocktemplate`) — the transactions your Knots+BIP-110 node would include in the next block. It does not sample the mempool.

Categories:

- **Economic / Clean** — no spam signals
- **Consolidations** — many inputs, few outputs
- **Coinjoins** — coinjoin patterns
- **Spam / Inscriptions** — inscriptions, large witness, OP_RETURN, BIP-110 violations

Displays: `Based on Block Template #HEIGHT · N txs · X% max weight`

## Block Template
<img width="892" height="255" alt="image" src="https://github.com/user-attachments/assets/d5d7818e-3903-4dc4-8479-de010e2581db" />


Compact GBT summary (height, txs, weight, coinbase, fees) and **top 5** transactions by fee rate. Press `t` to refresh.

## DATUM
<img width="895" height="390" alt="image" src="https://github.com/user-attachments/assets/ff5df15e-edae-4610-8936-0f49849d9fbf" />


```bash
sudo systemctl enable --now datum
```

In `bitcoin.conf`:

```
blocknotify=killall -USR1 datum_gateway
```

## tmux

```bash
tmux new -s oraculo 'oraculovision'
```

## Project structure

```
oraculovision/
├── main.py                 # Entry point
├── pyproject.toml          # Package metadata and install
├── config.example.toml     # Example configuration
├── requirements.txt        # Dependencies (reference)
├── install-shortcut.sh     # Global shortcut script
└── oraculovision/          # Python package
    ├── app.py              # Main Textual application
    ├── config.py           # Configuration loader
    ├── analysis/           # BIP-110, spam score, mempool
    ├── data/               # bitcoin-cli, DATUM, Ocean API
    ├── screens/            # Modals and help
    ├── services/           # Block template service
    ├── utils/              # Utilities (clipboard)
    └── widgets/            # Dashboard panels
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `bitcoin-cli not found` | Install Knots or set `BITCOIN_CLI` |
| Slow UTXO set | `gettxoutsetinfo` takes ~2 min; press `u` only when needed |
| Dashboard stutters on refresh | Use `r` for light refresh; reserve `t` and `u` for heavy RPCs |
| Slow Mempool Glass | Normal with ~1000 GBT txs (~2s); use `t` only when needed |
| Ocean stats missing | Set `[ocean].address` or press `o`; check network to api.ocean.xyz |
| Copy hash fails | Install `wl-copy` or `xclip` |
| Node uses ~5–8 GB RAM | Normal for a full Knots node with active mempool |

## License

MIT — see [LICENSE](LICENSE).
