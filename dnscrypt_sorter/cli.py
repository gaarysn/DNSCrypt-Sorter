from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .filters import SUPPORTED_PROTOCOLS, filter_resolvers
from .latency import ProbeOptions, measure_resolver
from .models import MeasurementResult, Resolver
from .source import SourceError, available_catalog_names, expand_catalogs, fetch_catalogs
from .ui import PromptBack, RunSummary, TerminalUI, render_plain_table


@dataclass(frozen=True, slots=True)
class ProbeProfile:
    attempts: int
    ping_delay: float
    server_delay: float
    timeout: float
    threaded_workers: int


@dataclass(frozen=True, slots=True)
class RunArtifacts:
    all_results: list[MeasurementResult]
    displayed_results: list[MeasurementResult]
    summary: RunSummary


@dataclass(slots=True)
class InteractiveWizardState:
    catalogs: tuple[str, ...] = ("public-resolvers",)
    protocols: tuple[str, ...] = ("DNSCrypt",)
    output_mode: str = "top"
    top: int = 50


PROBE_PROFILES: dict[str, ProbeProfile] = {
    "fast": ProbeProfile(attempts=2, ping_delay=0.0, server_delay=0.0, timeout=0.35, threaded_workers=24),
    "balanced": ProbeProfile(attempts=5, ping_delay=0.05, server_delay=0.02, timeout=0.75, threaded_workers=12),
    "deep": ProbeProfile(attempts=8, ping_delay=0.12, server_delay=0.05, timeout=1.2, threaded_workers=6),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure and rank official DNSCrypt catalogs with animated terminal progress, "
            "probe profiles and compact stamp rendering."
        )
    )
    parser.add_argument(
        "--catalog",
        action="append",
        choices=[*available_catalog_names(), "all"],
        dest="catalogs",
        help="official catalog to load; may be passed multiple times",
    )
    parser.add_argument(
        "--proto",
        action="append",
        choices=[*SUPPORTED_PROTOCOLS, "all"],
        dest="protocols",
        help="protocols to test; may be passed multiple times",
    )
    parser.add_argument("--list-catalogs", action="store_true", help="print supported official catalogs and exit")
    parser.add_argument("--list-protos", action="store_true", help="print supported protocol filters and exit")
    parser.add_argument("--cache-dir", default=".dnscrypt-cache", help="directory for cached catalog files")
    parser.add_argument("--filter-mode", choices=["strict", "catalog", "none"], default="strict", help="resolver filter profile")
    parser.add_argument("--profile", choices=tuple(PROBE_PROFILES), default="balanced", help="probe depth profile")
    parser.add_argument("-n", "--number-ping", type=int, help="override number of probe attempts per resolver")
    parser.add_argument("-p", "--ping-delay", type=float, help="override delay between attempts against the same resolver")
    parser.add_argument("-s", "--server-delay", type=float, help="override delay before probing each resolver")
    parser.add_argument("-m", "--time-out", type=float, help="override per-attempt timeout in seconds")
    parser.add_argument("-t", "--threading", action="store_true", help="probe multiple resolvers concurrently")
    parser.add_argument("--workers", type=int, help="maximum concurrent resolver probes")
    parser.add_argument("--top", type=int, default=50, help="number of fastest resolvers to print")
    parser.add_argument("--all", action="store_true", help="print every successful resolver instead of truncating to top N")
    parser.add_argument("--stamp-mode", choices=["compact", "full", "hidden"], default="compact", help="how to display sdns stamps in terminal output")
    parser.add_argument("--tcp-only", action="store_true", help="disable ICMP fallback and use only TCP connect latency")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON instead of a table")
    parser.add_argument("-v", "--verbose", action="store_true", help="print extra progress information")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ui = TerminalUI(enable_rich=not args.json)

    if args.list_catalogs:
        print("\n".join(available_catalog_names()))
        return 0
    if args.list_protos:
        print("\n".join(SUPPORTED_PROTOCOLS))
        return 0

    if args.number_ping is not None and args.number_ping <= 0:
        parser.error("--number-ping must be positive")
    if args.top <= 0:
        parser.error("--top must be positive")
    if args.time_out is not None and args.time_out <= 0:
        parser.error("--time-out must be positive")
    if (args.ping_delay is not None and args.ping_delay < 0) or (args.server_delay is not None and args.server_delay < 0):
        parser.error("delays must be non-negative")

    if should_prompt_for_selection(args):
        return run_interactive_wizard(args, ui)

    started = time.perf_counter()
    selected_catalogs, selected_protocols = resolve_selections(args, ui)
    artifacts = execute_run(
        args=args,
        ui=ui,
        selected_catalogs=selected_catalogs,
        selected_protocols=selected_protocols,
        output_mode="all" if args.all else "top",
        top=args.top,
    )
    if artifacts is None:
        return 1

    if args.json:
        print(render_json(artifacts.displayed_results))
    else:
        ui.print_results(artifacts.displayed_results, summary=artifacts.summary, stamp_mode=args.stamp_mode)

    if args.verbose:
        elapsed = time.perf_counter() - started
        print(f"\nCompleted in {elapsed:.2f}s", file=sys.stderr)

    return 0


def run_interactive_wizard(args: argparse.Namespace, ui: TerminalUI) -> int:
    state = InteractiveWizardState()
    step = "catalogs"

    while True:
        if step == "catalogs":
            state.catalogs = tuple(
                ui.prompt_multi_select(
                    "Select catalogs to download and test:",
                    options=available_catalog_names(),
                    default=state.catalogs,
                    allow_back=False,
                )
            )
            step = "protocols"
            continue

        if step == "protocols":
            try:
                state.protocols = tuple(
                    ui.prompt_multi_select(
                        "Select protocols to test:",
                        options=SUPPORTED_PROTOCOLS,
                        default=state.protocols,
                        allow_back=True,
                    )
                )
            except PromptBack:
                step = "catalogs"
                continue
            step = "output_mode"
            continue

        if step == "output_mode":
            try:
                output_choice = ui.prompt_single_select(
                    "How many results to show after the check?",
                    options=("Top N", "All results"),
                    default="Top N" if state.output_mode == "top" else "All results",
                    allow_back=True,
                )
            except PromptBack:
                step = "protocols"
                continue

            if output_choice == "All results":
                state.output_mode = "all"
                step = "run"
                continue

            state.output_mode = "top"
            try:
                state.top = int(
                    ui.prompt_text(
                        "Enter number of results to display",
                        default=str(state.top),
                        allow_back=True,
                        validator=validate_positive_int,
                    )
                )
            except PromptBack:
                step = "output_mode"
                continue
            step = "run"
            continue

        if step == "run":
            artifacts = execute_run(
                args=args,
                ui=ui,
                selected_catalogs=state.catalogs,
                selected_protocols=state.protocols,
                output_mode=state.output_mode,
                top=state.top,
            )
            if artifacts is None:
                ui.print_message("No results from the check. Returning to settings.", style="yellow")
                step = "output_mode"
                continue

            ui.print_results(artifacts.displayed_results, summary=artifacts.summary, stamp_mode=args.stamp_mode)
            next_action = handle_results_menu(ui, artifacts)
            if next_action == "main_menu":
                step = "catalogs"
                continue
            if next_action == "back":
                step = "output_mode"
                continue
            return 0


def resolve_probe_options(args: argparse.Namespace, profile: ProbeProfile) -> ProbeOptions:
    attempts = args.number_ping if args.number_ping is not None else profile.attempts
    ping_delay = args.ping_delay if args.ping_delay is not None else profile.ping_delay
    timeout = args.time_out if args.time_out is not None else profile.timeout
    return ProbeOptions(
        attempts=attempts,
        ping_delay=ping_delay,
        timeout=timeout,
        tcp_only=args.tcp_only,
    )


def resolve_server_delay(args: argparse.Namespace, profile: ProbeProfile) -> float:
    return args.server_delay if args.server_delay is not None else profile.server_delay


def resolve_workers(args: argparse.Namespace, profile: ProbeProfile) -> int:
    if args.workers is not None:
        return max(1, args.workers)
    if args.threading:
        return min(profile.threaded_workers, max(1, (os.cpu_count() or 4) * 2))
    return 1


def resolve_output_count(args: argparse.Namespace, total_results: int) -> int:
    if args.all:
        return total_results
    return min(args.top, total_results)


def resolve_output_count_for_mode(output_mode: str, top: int, total_results: int) -> int:
    if output_mode == "all":
        return total_results
    return min(top, total_results)


def describe_output_selection(output_mode: str, top: int, displayed_count: int) -> str:
    if output_mode == "all":
        return f"all ({displayed_count})"
    return f"top {top}"


def no_matches_message(
    filter_mode: str,
    catalogs: tuple[str, ...],
    protocols: tuple[str, ...],
) -> str:
    if filter_mode == "strict":
        return (
            "No resolvers matched the strict Europe/DNSCrypt/nofilter/nolog/IPv4 filter. "
            f"Selected catalogs: {', '.join(catalogs)}. Selected proto: {', '.join(protocols)}. "
            "Try a different catalog/proto set or use --filter-mode catalog / --filter-mode none."
        )
    return (
        "No measurable resolvers were found for the selected filters. "
        f"Catalogs: {', '.join(catalogs)}. Proto: {', '.join(protocols)}."
    )


def execute_run(
    args: argparse.Namespace,
    ui: TerminalUI,
    selected_catalogs: tuple[str, ...],
    selected_protocols: tuple[str, ...],
    output_mode: str,
    top: int,
) -> RunArtifacts | None:
    profile = PROBE_PROFILES[args.profile]
    options = resolve_probe_options(args, profile)
    workers = resolve_workers(args, profile)

    try:
        with ui.status("Loading official catalogs..."):
            catalog = fetch_catalogs(selected_catalogs, Path(args.cache_dir))
    except SourceError as exc:
        print(str(exc), file=sys.stderr)
        return None

    with ui.status("Applying resolver filters..."):
        filtered = filter_resolvers(catalog, mode=args.filter_mode, allowed_protocols=set(selected_protocols))
    if not filtered:
        print(no_matches_message(args.filter_mode, selected_catalogs, selected_protocols), file=sys.stderr)
        return None

    if args.verbose:
        print(f"Loaded {len(catalog)} resolvers from selected catalogs", file=sys.stderr)
        print(f"Filtered down to {len(filtered)} candidate resolvers", file=sys.stderr)
        print(f"Filter mode: {args.filter_mode}", file=sys.stderr)
        print(f"Protocols: {', '.join(selected_protocols)}", file=sys.stderr)
        print(f"Profile: {args.profile}", file=sys.stderr)
        print(f"Using {workers} worker(s)", file=sys.stderr)

    expected_attempts = len(filtered) * options.attempts
    with ui.create_probe_monitor(total=len(filtered), expected_attempts=expected_attempts) as monitor:
        ranked = rank_resolvers(
            filtered,
            options=options,
            workers=workers,
            server_delay=resolve_server_delay(args, profile),
            verbose=args.verbose,
            monitor=monitor,
        )

    if not ranked:
        print("No resolvers responded successfully.", file=sys.stderr)
        return None

    display_count = resolve_output_count_for_mode(output_mode, top, len(ranked))
    displayed = ranked[:display_count]
    return RunArtifacts(
        all_results=ranked,
        displayed_results=displayed,
        summary=RunSummary(
            catalogs=selected_catalogs,
            protocols=selected_protocols,
            output_selection=describe_output_selection(output_mode, top, len(displayed)),
            total_loaded=len(catalog),
            total_filtered=len(filtered),
            total_responded=len(ranked),
            total_displayed=len(displayed),
            filter_mode=args.filter_mode,
            profile=args.profile,
            expected_attempts=expected_attempts,
        ),
    )


def resolve_selections(args: argparse.Namespace, ui: TerminalUI) -> tuple[tuple[str, ...], tuple[str, ...]]:
    selected_catalogs = tuple(expand_catalogs(args.catalogs))
    selected_protocols = tuple(expand_protocols(args.protocols))
    if should_prompt_for_selection(args):
        selected_catalogs = tuple(
            ui.prompt_multi_select(
                "Select catalogs to download and test:",
                options=available_catalog_names(),
                default=(selected_catalogs[0],) if selected_catalogs else ("public-resolvers",),
            )
        )
        selected_protocols = tuple(
            ui.prompt_multi_select(
                "Select protocols to test:",
                options=SUPPORTED_PROTOCOLS,
                default=("DNSCrypt",),
            )
        )
    return selected_catalogs, selected_protocols


def expand_protocols(protocols: list[str] | None) -> list[str]:
    requested = list(protocols or ["DNSCrypt"])
    if "all" in requested:
        return list(SUPPORTED_PROTOCOLS)
    return requested


def should_prompt_for_selection(args: argparse.Namespace) -> bool:
    return (
        not args.json
        and not args.list_catalogs
        and not args.list_protos
        and args.catalogs is None
        and args.protocols is None
        and sys.stdin.isatty()
        and sys.stderr.isatty()
    )


def handle_results_menu(ui: TerminalUI, artifacts: RunArtifacts) -> str:
    while True:
        try:
            action = ui.prompt_single_select(
                "What to do next?",
                options=("Save result", "Back to main menu", "Exit"),
                default="Save result",
                allow_back=True,
            )
        except PromptBack:
            return "back"

        if action == "Save result":
            outcome = handle_save_menu(ui, artifacts)
            if outcome in {"main_menu", "exit"}:
                return outcome
            continue
        if action == "Back to main menu":
            return "main_menu"
        return "exit"


def handle_save_menu(ui: TerminalUI, artifacts: RunArtifacts) -> str:
    save_formats = ("txt", "json", "csv")
    default_paths = {
        "txt": "dnscrypt-results.txt",
        "json": "dnscrypt-results.json",
        "csv": "dnscrypt-results.csv",
    }

    while True:
        try:
            save_format = ui.prompt_single_select(
                "Select save format:",
                options=save_formats,
                default="json",
                allow_back=True,
            )
        except PromptBack:
            return "back"

        while True:
            try:
                destination = ui.prompt_text(
                    "Enter file path to save",
                    default=default_paths[save_format],
                    allow_back=True,
                    validator=validate_output_path,
                )
            except PromptBack:
                break

            save_results(artifacts, Path(destination), save_format)
            ui.print_message(f"Saved: {destination}", style="green")

            try:
                next_action = ui.prompt_single_select(
                    "What next?",
                    options=("Back to results", "Back to main menu", "Exit"),
                    default="Back to results",
                    allow_back=True,
                )
            except PromptBack:
                return "back"

            if next_action == "Back to main menu":
                return "main_menu"
            if next_action == "Exit":
                return "exit"
            return "back"


def save_results(artifacts: RunArtifacts, destination: Path, save_format: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if save_format == "json":
        destination.write_text(render_json(artifacts.displayed_results), encoding="utf-8")
        return
    if save_format == "txt":
        destination.write_text(build_text_export(artifacts), encoding="utf-8")
        return
    if save_format == "csv":
        write_csv_export(artifacts, destination)
        return
    raise ValueError(f"Unsupported save format: {save_format}")


def build_text_export(artifacts: RunArtifacts) -> str:
    summary_lines = [
        "Run Summary",
        f"catalogs: {', '.join(artifacts.summary.catalogs)}",
        f"proto: {', '.join(artifacts.summary.protocols)}",
        f"output: {artifacts.summary.output_selection}",
        f"filter: {artifacts.summary.filter_mode}",
        f"profile: {artifacts.summary.profile}",
        f"loaded: {artifacts.summary.total_loaded}",
        f"candidates: {artifacts.summary.total_filtered}",
        f"responded: {artifacts.summary.total_responded}",
        f"displayed: {artifacts.summary.total_displayed}",
        f"expected_probes: {artifacts.summary.expected_attempts}",
        "",
    ]
    return "\n".join(summary_lines) + render_plain_table(artifacts.displayed_results, stamp_mode="full")


def write_csv_export(artifacts: RunArtifacts, destination: Path) -> None:
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rank",
                "name",
                "catalog",
                "proto",
                "country",
                "address",
                "port",
                "latency_ms",
                "stderr_ms",
                "reliability_percent",
                "sdns",
            ]
        )
        for index, result in enumerate(artifacts.displayed_results, start=1):
            writer.writerow(
                [
                    index,
                    result.resolver.name,
                    result.resolver.catalog,
                    result.resolver.proto,
                    result.resolver.country,
                    result.address,
                    result.port,
                    round(result.latency_ms, 3),
                    round(result.stderr_ms, 3),
                    round(result.reliability_percent, 2),
                    result.resolver.stamp,
                ]
            )


def validate_positive_int(value: str) -> str:
    if not value.isdigit() or int(value) <= 0:
        raise ValueError("Enter a positive integer.")
    return value


def validate_output_path(value: str) -> str:
    path = Path(value).expanduser()
    if path.name in {"", ".", ".."}:
        raise ValueError("Enter a valid file path.")
    return str(path)


def rank_resolvers(
    resolvers: list[Resolver],
    options: ProbeOptions,
    workers: int,
    server_delay: float,
    verbose: bool,
    monitor=None,
) -> list[MeasurementResult]:
    results: list[MeasurementResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for index, resolver in enumerate(resolvers):
            if server_delay:
                time.sleep(server_delay)
            futures.append(executor.submit(measure_resolver, resolver, options))
            if monitor is not None:
                monitor.scheduled()
            if verbose and (index + 1) % 10 == 0:
                print(f"Scheduled {index + 1}/{len(resolvers)} resolvers", file=sys.stderr)

        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            if result is not None:
                results.append(result)
            if monitor is not None:
                monitor.completed(result)
            if verbose and index % 10 == 0:
                print(f"Collected {index}/{len(futures)} probe results", file=sys.stderr)

    return sorted(
        results,
        key=lambda item: (
            item.latency_seconds,
            -item.reliability,
            item.stderr_seconds,
            item.resolver.name,
        ),
    )


def render_json(results: list[MeasurementResult]) -> str:
    payload = [
        {
            "rank": index,
            "name": result.resolver.name,
            "catalog": result.resolver.catalog,
            "proto": result.resolver.proto,
            "country": result.resolver.country,
            "address": result.address,
            "port": result.port,
            "latency_ms": round(result.latency_ms, 3),
            "stderr_ms": round(result.stderr_ms, 3),
            "reliability_percent": round(result.reliability_percent, 2),
            "sdns": result.resolver.stamp,
        }
        for index, result in enumerate(results, start=1)
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)
