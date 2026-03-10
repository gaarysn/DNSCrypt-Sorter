import unittest
from argparse import Namespace
import json
import tempfile
from pathlib import Path

from dnscrypt_sorter.cli import (
    PROBE_PROFILES,
    RunArtifacts,
    build_text_export,
    describe_output_selection,
    expand_protocols,
    resolve_output_count,
    resolve_probe_options,
    save_results,
    should_prompt_for_selection,
    validate_positive_int,
)
from dnscrypt_sorter.models import GeoLocation, MeasurementResult, Resolver
from dnscrypt_sorter.ui import RunSummary, compact_stamp, parse_multi_select


def make_result() -> MeasurementResult:
    resolver = Resolver(
        catalog="public-resolvers",
        name="dnscry.pt-paris-ipv4",
        proto="DNSCrypt",
        stamp="sdns://AQcAAAAAAAAA",
        country="France",
        description="Paris, France DNSCrypt resolver",
        dnssec=True,
        nofilter=True,
        nolog=True,
        ipv6=False,
        addrs=("51.158.147.132",),
        ports=(443,),
        location=GeoLocation(lat=48.8566, lon=2.3522),
    )
    return MeasurementResult(
        resolver=resolver,
        address="51.158.147.132",
        port=443,
        latency_seconds=0.05,
        stderr_seconds=0.005,
        reliability=1.0,
        successful_attempts=3,
        attempted_probes=3,
    )


class CliHelpersTests(unittest.TestCase):
    def test_resolve_output_count_supports_top_and_all(self) -> None:
        self.assertEqual(resolve_output_count(Namespace(all=False, top=10), 87), 10)
        self.assertEqual(resolve_output_count(Namespace(all=True, top=10), 87), 87)

    def test_probe_profile_can_be_overridden(self) -> None:
        options = resolve_probe_options(
            Namespace(number_ping=None, ping_delay=None, time_out=None, tcp_only=False),
            PROBE_PROFILES["balanced"],
        )
        self.assertEqual(options.attempts, PROBE_PROFILES["balanced"].attempts)

        overridden = resolve_probe_options(
            Namespace(number_ping=9, ping_delay=0.2, time_out=1.5, tcp_only=True),
            PROBE_PROFILES["fast"],
        )
        self.assertEqual(overridden.attempts, 9)
        self.assertEqual(overridden.ping_delay, 0.2)
        self.assertEqual(overridden.timeout, 1.5)
        self.assertTrue(overridden.tcp_only)

    def test_compact_stamp_shortens_long_values(self) -> None:
        stamp = "sdns://ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        compact = compact_stamp(stamp, prefix=8, suffix=6)
        self.assertTrue(compact.startswith("sdns://A"))
        self.assertTrue(compact.endswith("456789"))
        self.assertIn("...", compact)

    def test_expand_protocols_supports_all_alias(self) -> None:
        self.assertEqual(expand_protocols(None), ["DNSCrypt"])
        expanded = expand_protocols(["all"])
        self.assertIn("DNSCrypt", expanded)
        self.assertIn("ODoH relay", expanded)

    def test_should_prompt_only_without_explicit_selection(self) -> None:
        args = Namespace(json=False, list_catalogs=False, list_protos=False, catalogs=None, protocols=None)
        self.assertIsInstance(should_prompt_for_selection(args), bool)

    def test_parse_multi_select_returns_selected_values(self) -> None:
        values = parse_multi_select("1,3", ["a", "b", "c"])
        self.assertEqual(values, ["a", "c"])

    def test_describe_output_selection_supports_top_and_all(self) -> None:
        self.assertEqual(describe_output_selection("top", 10, 10), "top 10")
        self.assertEqual(describe_output_selection("all", 10, 87), "all (87)")

    def test_validate_positive_int_rejects_invalid_values(self) -> None:
        self.assertEqual(validate_positive_int("15"), "15")
        with self.assertRaises(ValueError):
            validate_positive_int("0")

    def test_save_results_supports_txt_json_and_csv(self) -> None:
        result = make_result()
        artifacts = RunArtifacts(
            all_results=[result],
            displayed_results=[result],
            summary=RunSummary(
                catalogs=("public-resolvers",),
                protocols=("DNSCrypt",),
                output_selection="top 1",
                total_loaded=1,
                total_filtered=1,
                total_responded=1,
                total_displayed=1,
                filter_mode="strict",
                profile="balanced",
                expected_attempts=3,
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            txt_path = Path(tmp) / "result.txt"
            json_path = Path(tmp) / "result.json"
            csv_path = Path(tmp) / "result.csv"
            save_results(artifacts, txt_path, "txt")
            save_results(artifacts, json_path, "json")
            save_results(artifacts, csv_path, "csv")

            self.assertIn("Run Summary", txt_path.read_text(encoding="utf-8"))
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["proto"], "DNSCrypt")
            self.assertIn("sdns", csv_path.read_text(encoding="utf-8"))

    def test_build_text_export_contains_output_selection(self) -> None:
        result = make_result()
        artifacts = RunArtifacts(
            all_results=[result],
            displayed_results=[result],
            summary=RunSummary(
                catalogs=("public-resolvers",),
                protocols=("DNSCrypt",),
                output_selection="all (1)",
                total_loaded=1,
                total_filtered=1,
                total_responded=1,
                total_displayed=1,
                filter_mode="strict",
                profile="balanced",
                expected_attempts=3,
            ),
        )
        text = build_text_export(artifacts)
        self.assertIn("output: all (1)", text)


if __name__ == "__main__":
    unittest.main()
