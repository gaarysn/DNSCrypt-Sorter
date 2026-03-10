from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GeoLocation:
    lat: float
    lon: float

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "GeoLocation | None":
        if not isinstance(payload, dict):
            return None

        lat = payload.get("lat")
        lon = payload.get("long")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return None
        return cls(lat=float(lat), lon=float(lon))


@dataclass(frozen=True, slots=True)
class Resolver:
    catalog: str
    name: str
    proto: str
    stamp: str
    country: str
    description: str
    dnssec: bool
    nofilter: bool
    nolog: bool
    ipv6: bool
    addrs: tuple[str, ...]
    ports: tuple[int, ...]
    location: GeoLocation | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Resolver":
        addrs = tuple(str(value) for value in payload.get("addrs", []) if isinstance(value, str))
        ports = tuple(int(value) for value in payload.get("ports", []) if isinstance(value, int))

        return cls(
            catalog=str(payload.get("catalog", "public-resolvers")),
            name=str(payload.get("name", "")),
            proto=str(payload.get("proto", "")),
            stamp=str(payload.get("stamp", "")),
            country=str(payload.get("country", "")),
            description=str(payload.get("description", "")),
            dnssec=bool(payload.get("dnssec", False)),
            nofilter=bool(payload.get("nofilter", False)),
            nolog=bool(payload.get("nolog", False)),
            ipv6=bool(payload.get("ipv6", False)),
            addrs=addrs,
            ports=ports,
            location=GeoLocation.from_dict(payload.get("location")),
        )


@dataclass(frozen=True, slots=True)
class MeasurementResult:
    resolver: Resolver
    address: str
    port: int | None
    latency_seconds: float
    stderr_seconds: float
    reliability: float
    successful_attempts: int
    attempted_probes: int

    @property
    def latency_ms(self) -> float:
        return self.latency_seconds * 1000.0

    @property
    def stderr_ms(self) -> float:
        return self.stderr_seconds * 1000.0

    @property
    def reliability_percent(self) -> float:
        return self.reliability * 100.0
