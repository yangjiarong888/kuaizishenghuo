"""External-data contract for takeout delivery addresses."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping


TAKEOUT_ADDRESS_ENV_KEYS = (
    "BUSINESS_ADDRESS_SEARCH",
    "BUSINESS_ADDRESS_CONTACT",
    "TAKEOUT_ADDRESS_CONTACT",
    "TAKEOUT_ADDRESS_PHONE",
    "TAKEOUT_ADDRESS_SEARCH",
    "TAKEOUT_ADDRESS_DETAIL",
    "MALL_TEST_ADDRESS_QUERY",
)


class TakeoutAddressPolicy(str, Enum):
    EXISTING = "existing"
    AUTO = "auto"
    ADD = "add"


@dataclass(frozen=True)
class TakeoutAddressData:
    contact: str = ""
    phone: str = ""
    search: str = ""
    detail: str = ""

    def missing_for_add(self) -> tuple[str, ...]:
        fields = ("contact", "phone", "search", "detail")
        return tuple(name for name in fields if not getattr(self, name).strip())


def load_takeout_address_data(environ: Mapping[str, str]) -> TakeoutAddressData:
    return TakeoutAddressData(
        contact=(
            environ.get("BUSINESS_ADDRESS_CONTACT", "").strip()
            or environ.get("TAKEOUT_ADDRESS_CONTACT", "").strip()
        ),
        phone=environ.get("TAKEOUT_ADDRESS_PHONE", "").strip(),
        search=resolve_business_address_search(
            environ, "TAKEOUT_ADDRESS_SEARCH"
        ),
        detail=environ.get("TAKEOUT_ADDRESS_DETAIL", "").strip(),
    )


def resolve_business_address_search(
    environ: Mapping[str, str], specific_key: str
) -> str:
    return (
        environ.get("BUSINESS_ADDRESS_SEARCH", "").strip()
        or environ.get(specific_key, "").strip()
    )


def load_takeout_address_environment(
    environ: Mapping[str, str],
    *,
    dotenv_path: Path,
) -> dict[str, str]:
    """Load only takeout address keys; process values override local `.env`."""
    loaded: dict[str, str] = {}
    if dotenv_path.is_file():
        for raw_line in dotenv_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in TAKEOUT_ADDRESS_ENV_KEYS:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            loaded[key] = value
    for key in TAKEOUT_ADDRESS_ENV_KEYS:
        if key in environ:
            loaded[key] = str(environ[key])
    return loaded
