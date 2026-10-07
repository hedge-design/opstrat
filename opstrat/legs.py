"""Option leg model and input normalisation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

OpType = Literal["c", "p"]
TrType = Literal["b", "s"]

NAMES = {"c": "Call", "p": "Put", "b": "Long", "s": "Short"}


def check_optype(op_type: str) -> str:
    op_type = str(op_type).lower()
    if op_type not in ("c", "p"):
        raise ValueError("Input 'p' for put and 'c' for call!")
    return op_type


def check_trtype(tr_type: str) -> str:
    tr_type = str(tr_type).lower()
    if tr_type not in ("b", "s"):
        raise ValueError("Input 'b' for Buy and 's' for Sell!")
    return tr_type


@dataclass(frozen=True)
class Leg:
    """A single option position.

    Parameters
    ----------
    op_type : {'c', 'p'}
        Call or put.
    strike : float
        Strike price.
    tr_type : {'b', 's'}
        Long ('b') or short ('s').
    op_pr : float
        Premium paid / received per unit.
    contracts : float
        Number of contracts (payoff is scaled linearly).
    """

    op_type: OpType
    strike: float
    tr_type: TrType = "b"
    op_pr: float = 0.0
    contracts: float = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "op_type", check_optype(self.op_type))
        object.__setattr__(self, "tr_type", check_trtype(self.tr_type))
        if self.strike <= 0:
            raise ValueError("strike must be positive")
        if self.contracts <= 0:
            raise ValueError("contracts must be positive")

    @property
    def sign(self) -> int:
        return 1 if self.tr_type == "b" else -1

    @property
    def label(self) -> str:
        n = f"{self.contracts:g}"
        return f"{n} {NAMES[self.tr_type]} {NAMES[self.op_type]} K={self.strike:g}"

    @classmethod
    def from_dict(cls, d: Mapping) -> Leg:
        """Build a leg from the classic opstrat dict format.

        Accepts both ``'contract'`` (legacy) and ``'contracts'`` keys.
        """
        contracts = d.get("contracts", d.get("contract", 1))
        return cls(
            op_type=d["op_type"],
            strike=float(d["strike"]),
            tr_type=d.get("tr_type", "b"),
            op_pr=float(d.get("op_pr", 0.0)),
            contracts=contracts,
        )


def to_legs(op_list: Iterable[Leg | Mapping]) -> list[Leg]:
    legs = [op if isinstance(op, Leg) else Leg.from_dict(op) for op in op_list]
    if not legs:
        raise ValueError("op_list must contain at least one option")
    return legs
