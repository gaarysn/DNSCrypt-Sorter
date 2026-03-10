import unittest

from dnscrypt_sorter.filters import filter_resolvers, is_target_resolver
from dnscrypt_sorter.models import GeoLocation, Resolver


def make_resolver(**overrides) -> Resolver:
    payload = {
        "catalog": "public-resolvers",
        "name": "dnscry.pt-paris-ipv4",
        "proto": "DNSCrypt",
        "stamp": "sdns://AQcAAAAAAAAA",
        "country": "France",
        "description": "Paris, France DNSCrypt resolver",
        "dnssec": True,
        "nofilter": True,
        "nolog": True,
        "ipv6": False,
        "addrs": ("51.158.147.132",),
        "ports": (443,),
        "location": GeoLocation(lat=48.8566, lon=2.3522),
    }
    payload.update(overrides)
    return Resolver(**payload)


class FilterResolversTests(unittest.TestCase):
    def test_accepts_strict_european_dnscrypt_resolver(self) -> None:
        resolver = make_resolver()
        self.assertTrue(is_target_resolver(resolver))

    def test_rejects_ipv6_and_non_european_coordinates(self) -> None:
        ipv6_resolver = make_resolver(ipv6=True, addrs=("[2001:db8::1]",))
        remote_resolver = make_resolver(
            country="France",
            location=GeoLocation(lat=-33.8688, lon=151.2093),
        )

        self.assertFalse(is_target_resolver(ipv6_resolver))
        self.assertFalse(is_target_resolver(remote_resolver))

    def test_filter_resolvers_keeps_only_matching_candidates(self) -> None:
        candidates = [
            make_resolver(),
            make_resolver(name="relay", proto="DNSCrypt relay"),
            make_resolver(name="missing-stamp", stamp=""),
            make_resolver(name="with-logs", nolog=False),
        ]

        filtered = filter_resolvers(candidates)

        self.assertEqual([resolver.name for resolver in filtered], ["dnscry.pt-paris-ipv4"])

    def test_catalog_and_none_modes_allow_broader_selection(self) -> None:
        relay = make_resolver(
            catalog="relays",
            name="anon-cs-berlin",
            proto="DNSCrypt relay",
            nolog=False,
            nofilter=False,
            description="Berlin, Germany Anonymized DNS relay server",
        )

        self.assertTrue(is_target_resolver(relay, mode="catalog"))
        self.assertTrue(is_target_resolver(relay, mode="none"))

    def test_allowed_protocols_filter_is_applied(self) -> None:
        dnscrypt = make_resolver(proto="DNSCrypt")
        doh = make_resolver(name="doh-sample", proto="DoH")

        filtered = filter_resolvers([dnscrypt, doh], mode="catalog", allowed_protocols={"DoH"})

        self.assertEqual([resolver.name for resolver in filtered], ["doh-sample"])


if __name__ == "__main__":
    unittest.main()
