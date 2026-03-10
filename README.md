# DNSCrypt-Sorter

```
 ____  _   _ ____                       _     ____             _
|  _ \| \ | / ___|  ___ _ __ _   _ _ __ | |_  / ___|  ___  _ __| |_ ___ _ __
| | | |  \| \___ \ / __| '__| | | | '_ \| __| \___ \ / _ \| '__| __/ _ \ '__|
| |_| | |\  |___) | (__| |  | |_| | |_) | |_   ___) | (_) | |  | ||  __/ |
|____/|_| \_|____/ \___|_|   \__, | .__/ \__| |____/ \___/|_|   \__\___|_|
                              |___/|_|
```

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![Version 0.5.0](https://img.shields.io/badge/version-0.5.0-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

**Measure and rank DNS resolvers from official DNSCrypt catalogs by latency.**

DNSCrypt-Sorter loads resolver lists published at [dnscrypt.info](https://dnscrypt.info/), probes each server with TCP/ICMP pings, and presents results sorted by response time in a modern terminal UI.

---

## Features

- **Official catalogs** — `public-resolvers`, `relays`, `parental-control`, `opennic`, `onion-services`, `odoh-servers`, `odoh-relays`
- **Multiple protocols** — DNSCrypt, DoH, ODoH, DNSCrypt relay, ODoH relay
- **Flexible filters** — nofilter, nolog, DNSSEC, IPv4/IPv6, country
- **Probe profiles** — `fast`, `balanced`, `deep` presets with manual overrides
- **Interactive wizard** — step-by-step selection with back navigation (`0`) and `Ctrl+C` to return to main menu
- **IP check** — view local and public IP addresses from the main menu
- **Rich terminal UI** — animated progress, live counters, color-coded output, adaptive ASCII banner
- **Export** — save results as TXT, JSON, or CSV with auto-generated filenames into `dnscrypt-results/`

---

## Quick Start

```bash
git clone https://github.com/Magalame/Dnscrypt-list-ping-sorting.git
cd Dnscrypt-list-ping-sorting
python3 -m pip install -e .
```

Launch the interactive wizard:

```bash
dnscrypt-sorter
```

Or run directly:

```bash
python3 ping_dnscrypt.py
```

---

## Interactive Wizard

The default flow when running without flags:

| Step | Action |
|------|--------|
| 1 | Main menu — **Start new check** or **Check IP** |
| 2 | Select one or more catalogs |
| 3 | Select one or more protocols |
| 4 | Apply optional filters (or skip with *I don't know*) |
| 5 | Choose result size — Top N or All |
| 6 | Latency check runs with live progress |
| 7 | View results, save, or return to main menu |

- Type **`0`** at any step to go back.
- Press **`Ctrl+C`** to return to the main menu; press again to exit.

---

## CLI Reference

```bash
python3 ping_dnscrypt.py [OPTIONS]
```

### Catalogs & Protocols

| Flag | Description |
|------|-------------|
| `--catalog NAME` | Select a catalog (repeatable) |
| `--catalog all` | Load all catalogs |
| `--list-catalogs` | Print available catalog names |
| `--proto NAME` | Select a protocol (repeatable) |
| `--list-protos` | Print available protocol names |

### Filters

| Flag | Description |
|------|-------------|
| `--require-nofilter` | Only resolvers with no filtering |
| `--require-nolog` | Only resolvers with no logging |
| `--dnssec-only` | Only DNSSEC-validating resolvers |
| `--ip-version any\|ipv4\|ipv6` | Filter by IP version |
| `--country NAME` | Filter by country (repeatable) |

### Probing

| Flag | Description |
|------|-------------|
| `--profile fast\|balanced\|deep` | Probe profile preset |
| `-n`, `--number-ping` | Number of probe attempts |
| `-p`, `--ping-delay` | Delay between pings (seconds) |
| `-s`, `--server-delay` | Delay between servers (seconds) |
| `-m`, `--time-out` | Probe timeout (seconds) |
| `--workers` | Concurrent worker threads |
| `--tcp-only` | Disable ICMP fallback |

### Output

| Flag | Description |
|------|-------------|
| `--top N` | Show fastest N results |
| `--all` | Show all successful results |
| `--stamp-mode compact\|full\|hidden` | SDNS stamp display mode |
| `--json` | Emit JSON output |
| `--cache-dir PATH` | Catalog cache directory |

### Examples

Top 10 DNSCrypt resolvers with no filtering and no logging, IPv4 only:

```bash
python3 ping_dnscrypt.py \
  --catalog public-resolvers \
  --proto DNSCrypt \
  --require-nofilter --require-nolog \
  --ip-version ipv4 \
  --profile balanced -t --top 10
```

All DoH endpoints in Germany:

```bash
python3 ping_dnscrypt.py \
  --catalog all --proto DoH \
  --country Germany \
  --profile deep -t --all
```

JSON output with full stamps:

```bash
python3 ping_dnscrypt.py \
  --catalog public-resolvers --proto all \
  --top 25 --json
```

---

## Probe Profiles

| Profile | Attempts | Timeout | Workers | Use case |
|---------|----------|---------|---------|----------|
| `fast` | 3 | 2 s | 32 | Quick scan |
| `balanced` | 5 | 3 s | 16 | Default |
| `deep` | 10 | 5 s | 8 | Thorough analysis |

Override any preset parameter with the corresponding flag.

---

## Saving Results

In interactive mode the wizard offers to save after displaying results. The default filename is auto-generated:

```
dnscrypt-results/20260310-public-resolvers-dnscrypt-nofilter-nolog.csv
```

The `dnscrypt-results/` directory is created automatically and is listed in `.gitignore`.

---

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
python3 -m pytest tests/ -v
```

---

## Credits

Original project by [Magalame](https://github.com/Magalame/Dnscrypt-list-ping-sorting) — a program to ping and sort the DNS servers proposed by [dnscrypt.info](https://dnscrypt.info/). Many thanks to the original author for the idea and the initial implementation.
