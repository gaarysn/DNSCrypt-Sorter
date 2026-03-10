from __future__ import annotations

from typing import Iterable

from .models import Resolver

SUPPORTED_PROTOCOLS = (
    "DNSCrypt",
    "DoH",
    "ODoH",
    "DNSCrypt relay",
    "ODoH relay",
)

EUROPEAN_COUNTRIES = {
    "Albania",
    "Andorra",
    "Austria",
    "Belarus",
    "Belgium",
    "Bosnia and Herzegovina",
    "Bulgaria",
    "Croatia",
    "Cyprus",
    "Czech Republic",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Hungary",
    "Iceland",
    "Ireland",
    "Italy",
    "Kosovo",
    "Latvia",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Moldova",
    "Monaco",
    "Montenegro",
    "Netherlands",
    "North Macedonia",
    "Norway",
    "Poland",
    "Portugal",
    "Romania",
    "San Marino",
    "Serbia",
    "Slovakia",
    "Slovenia",
    "Spain",
    "Sweden",
    "Switzerland",
    "Ukraine",
    "United Kingdom",
    "Vatican City",
    "Isle of Man",
}


def filter_resolvers(
    resolvers: Iterable[Resolver],
    mode: str = "strict",
    allowed_protocols: set[str] | None = None,
) -> list[Resolver]:
    return [
        resolver
        for resolver in resolvers
        if is_target_resolver(resolver, mode=mode, allowed_protocols=allowed_protocols)
    ]


def is_target_resolver(
    resolver: Resolver,
    mode: str = "strict",
    allowed_protocols: set[str] | None = None,
) -> bool:
    if allowed_protocols is not None and resolver.proto not in allowed_protocols:
        return False
    if mode == "none":
        return is_measurable(resolver)
    if mode == "catalog":
        return is_catalog_candidate(resolver)
    if mode != "strict":
        raise ValueError(f"Unsupported filter mode: {mode}")

    if resolver.proto != "DNSCrypt":
        return False
    if not resolver.nofilter or not resolver.nolog:
        return False
    if not is_measurable(resolver):
        return False
    if resolver.country not in EUROPEAN_COUNTRIES:
        return False
    if not has_european_evidence(resolver):
        return False
    return True


def is_catalog_candidate(resolver: Resolver) -> bool:
    return is_measurable(resolver)


def is_measurable(resolver: Resolver) -> bool:
    if not resolver.stamp.startswith("sdns://"):
        return False
    if resolver.ipv6:
        return False
    if not resolver.addrs:
        return False
    return True


def has_european_evidence(resolver: Resolver) -> bool:
    if resolver.location is not None:
        return is_european_coordinate(resolver.location.lat, resolver.location.lon)
    if resolver.country not in EUROPEAN_COUNTRIES:
        return False
    return resolver.country.lower() in resolver.description.lower() or resolver.country.lower() in resolver.name.lower()


def is_european_coordinate(lat: float, lon: float) -> bool:
    # Broad enough to include Iceland, Cyprus and the Canary Islands while
    # excluding clearly non-European locations.
    return 27.0 <= lat <= 72.5 and -31.5 <= lon <= 45.5
