# Dnscrypt-list-ping-sorting

CLI utility for loading official DNSCrypt catalogs, checking latency with visible probe progress, and showing results in a modern terminal UI with compact `sdns://...` stamps.

## Supported catalogs

The tool can now load the official DNSCrypt catalogs directly:

- `public-resolvers`
- `relays`
- `parental-control`
- `opennic`
- `onion-services`
- `odoh-servers`
- `odoh-relays`

By default an interactive selection screen is shown when you run:

```bash
python3 ping_dnscrypt.py
```

There you can choose multiple catalogs and multiple protocols to test. The interactive wizard now also lets you:

- choose whether to show `top N` or all results
- save the final result as `txt`, `json` or `csv`
- go back to the previous step with `back`
- return to the main menu after results

You can still select catalogs explicitly with flags or use `--catalog all`.

## Protocol selection

Protocols can now be selected explicitly, including multiple values:

- `DNSCrypt`
- `DoH`
- `ODoH`
- `DNSCrypt relay`
- `ODoH relay`

You can pass `--proto` multiple times, or choose them interactively on startup.

## Filter modes

Three filter modes are available:

- `strict`: strict Europe + `DNSCrypt` + `nofilter` + `nolog` + `IPv4`
- `catalog`: broader measurable candidates from the selected catalogs
- `none`: only require a measurable non-IPv6 endpoint with a valid `sdns://` stamp

The default remains `strict`.

## Probe profiles

To avoid checks that feel too fast and opaque, the tool now has explicit probe profiles:

- `fast`
- `balanced`
- `deep`

These presets control attempt count, delays, timeout and the default threaded worker budget. You can still override them manually with:

- `-n`, `--number-ping`
- `-p`, `--ping-delay`
- `-s`, `--server-delay`
- `-m`, `--time-out`
- `--workers`

Latency is measured by:

1. TCP connect latency against the decoded resolver host/port.
2. ICMP fallback if TCP probing fails, unless `--tcp-only` is enabled.
3. Repeated probing with mean latency, standard error and reliability.

## Terminal UI

Terminal output now includes:

- animated progress while catalogs are loading and resolvers are being checked
- live counters for successful and failed checks
- compact stamp rendering so long `sdns://...` values no longer break terminal width
- optional full stamp display when needed

Progress is written to `stderr`, so machine-readable output can still be redirected safely from `stdout`.

## Usage

Run the legacy entry point:

```bash
python3 ping_dnscrypt.py --catalog public-resolvers --profile balanced -t --top 10
```

Or use the package entry point:

```bash
python3 -m dnscrypt_sorter.cli --catalog all --filter-mode catalog --profile deep -t --all
```

Useful options:

- `--catalog NAME`: select an official catalog, repeatable
- `--catalog all`: load all official catalogs
- `--list-catalogs`: print supported catalog names
- `--proto NAME`: select protocol to test, repeatable
- `--list-protos`: print supported protocol names
- `--filter-mode strict|catalog|none`
- `--profile fast|balanced|deep`
- `--top N`: print the fastest `N` results
- `--all`: print all successful results
- `--stamp-mode compact|full|hidden`
- `--json`: emit JSON instead of terminal UI
- `--cache-dir PATH`: directory used to cache downloaded catalogs

## Interactive wizard flow

The default interactive flow is now:

1. choose one or more catalogs
2. choose one or more protocols
3. choose result size: `top N` or `all`
4. run checks
5. save results or return to the main menu

At every wizard step after the first one you can type `back` to return to the previous menu.

Examples:

Check strict European DNSCrypt resolvers and show only top 10:

```bash
python3 ping_dnscrypt.py --catalog public-resolvers --proto DNSCrypt --profile balanced -t --top 10
```

Check all official catalogs with a broader filter and print everything:

```bash
python3 ping_dnscrypt.py --catalog all --proto all --filter-mode catalog --profile deep -t --all
```

Emit JSON with full stamps:

```bash
python3 ping_dnscrypt.py --catalog public-resolvers --top 25 --json
```

Save results non-interactively by redirecting output if needed, or use the built-in wizard save step in interactive mode.

## Development

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Install as a local package:

```bash
python3 -m pip install -e .
```
