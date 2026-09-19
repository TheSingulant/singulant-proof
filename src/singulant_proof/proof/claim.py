"""V1 claim surface. No freeform NL claims. No trading / wallet / TX claims."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

CLAIM_ID: Final = "SMART_MONEY_IS_ACCUMULATING_THIS_TOKEN"
CLAIM_DISPLAY: Final = "Smart Money is accumulating this token."


class Verdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    SUPPORTED_BUT_CONTESTED = "SUPPORTED_BUT_CONTESTED"
    MIXED = "MIXED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ClaimError(ValueError):
    pass


@dataclass(frozen=True)
class Claim:
    id: str
    display: str

    def as_public_dict(self) -> dict[str, str]:
        return {"id": self.id, "display": self.display}


V1_CLAIM = Claim(id=CLAIM_ID, display=CLAIM_DISPLAY)


def parse_claim(value: str | None) -> Claim:
    if value is None or value == "" or value == CLAIM_ID:
        return V1_CLAIM
    raise ClaimError(
        f"unsupported claim {value!r}; V1 accepts only {CLAIM_ID}"
    )
