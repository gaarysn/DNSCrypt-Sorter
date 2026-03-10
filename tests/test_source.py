import unittest

from dnscrypt_sorter.source import expand_catalogs, parse_catalog, parse_markdown_catalog


class ParseCatalogTests(unittest.TestCase):
    def test_parse_catalog_ignores_invalid_items(self) -> None:
        raw_items = [
            "not-a-dict",
            {"name": "missing-stamp"},
            {
                "name": "resolver-1",
                "stamp": "sdns://AQcAAAAAAAAA",
                "proto": "DNSCrypt",
                "country": "France",
                "description": "Paris, France",
                "dnssec": True,
                "nofilter": True,
                "nolog": True,
                "ipv6": False,
                "addrs": ["51.158.147.132"],
                "ports": [443],
                "location": {"lat": 48.8566, "long": 2.3522},
            },
        ]

        resolvers = list(parse_catalog(raw_items))

        self.assertEqual(len(resolvers), 1)
        self.assertEqual(resolvers[0].name, "resolver-1")
        self.assertEqual(resolvers[0].ports, (443,))
        self.assertEqual(resolvers[0].catalog, "public-resolvers")

    def test_parse_markdown_catalog_decodes_dnscrypt_stamp(self) -> None:
        markdown = """
## ibksturm

Switzerland, running by ibksturm, Opennic, nologs, DNSSEC

sdns://AQcAAAAAAAAAEzIxMy4xOTYuMTkxLjk2Ojg0NDMgQg5eFucIAx7hJqzl4olTm-o1y4qE7eThMBlzuZ4e_acYMi5kbnNjcnlwdC1jZXJ0Lmlia3N0dXJt
"""
        resolvers = list(parse_markdown_catalog(markdown, catalog_name="opennic"))

        self.assertEqual(len(resolvers), 1)
        self.assertEqual(resolvers[0].catalog, "opennic")
        self.assertEqual(resolvers[0].proto, "DNSCrypt")
        self.assertEqual(resolvers[0].country, "Switzerland")
        self.assertEqual(resolvers[0].addrs, ("213.196.191.96",))
        self.assertEqual(resolvers[0].ports, (8443,))

    def test_expand_catalogs_supports_all_alias(self) -> None:
        expanded = expand_catalogs(["all"])
        self.assertIn("public-resolvers", expanded)
        self.assertIn("odoh-relays", expanded)


if __name__ == "__main__":
    unittest.main()
