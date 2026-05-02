"""Lambda Python runtime lifecycle table. Primary source: AWS Lambda runtimes docs.

Dates reflect published AWS Lambda runtime deprecation schedule.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional


@dataclass
class RuntimeInfo:
    name: str  # e.g. "python3.10"
    python_version: str  # e.g. "3.10"
    deprecation_phase1: Optional[date]  # end of support — no more security patches
    block_create: Optional[date]  # AWS blocks creating NEW functions
    block_update: Optional[date]  # AWS blocks updating EXISTING functions
    recommended_target: str = "python3.12"


RUNTIME_TABLE: Dict[str, RuntimeInfo] = {
    "python3.7": RuntimeInfo(
        "python3.7",
        "3.7",
        deprecation_phase1=date(2023, 11, 27),
        block_create=date(2023, 12, 28),
        block_update=date(2024, 1, 29),
    ),
    "python3.8": RuntimeInfo(
        "python3.8",
        "3.8",
        deprecation_phase1=date(2024, 10, 14),
        block_create=date(2024, 11, 13),
        block_update=date(2024, 12, 16),
    ),
    "python3.9": RuntimeInfo(
        "python3.9",
        "3.9",
        deprecation_phase1=date(2025, 12, 15),
        block_create=date(2026, 1, 14),
        block_update=date(2026, 2, 13),
    ),
    "python3.10": RuntimeInfo(
        "python3.10",
        "3.10",
        deprecation_phase1=date(2026, 10, 31),
        block_create=date(2026, 11, 30),
        block_update=date(2026, 12, 31),
    ),
    "python3.11": RuntimeInfo(
        "python3.11",
        "3.11",
        deprecation_phase1=date(2027, 6, 30),
        block_create=date(2027, 7, 30),
        block_update=date(2027, 8, 31),
    ),
    "python3.12": RuntimeInfo(
        "python3.12",
        "3.12",
        deprecation_phase1=None,
        block_create=None,
        block_update=None,
        recommended_target="python3.12",
    ),
    "python3.13": RuntimeInfo(
        "python3.13",
        "3.13",
        deprecation_phase1=None,
        block_create=None,
        block_update=None,
        recommended_target="python3.13",
    ),
}


def days_until(d: Optional[date]) -> Optional[int]:
    if d is None:
        return None
    return (d - date.today()).days


def severity_for(runtime: str) -> str:
    info = RUNTIME_TABLE.get(runtime)
    if not info or not info.deprecation_phase1:
        return "ok"
    days = days_until(info.deprecation_phase1)
    if days is None:
        return "ok"
    if days < 0:
        return "critical-eol"
    if days <= 30:
        return "critical"
    if days <= 90:
        return "high"
    if days <= 180:
        return "medium"
    return "low"


def is_eol_or_soon(runtime: str) -> bool:
    sev = severity_for(runtime)
    return sev in ("critical", "critical-eol", "high", "medium")
