from decimal import Decimal, ROUND_HALF_UP

MONEY_QUANTUM = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Return a two-decimal monetary amount without ever using float arithmetic."""
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
