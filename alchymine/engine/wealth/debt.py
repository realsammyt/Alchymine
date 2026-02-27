"""Debt payoff engine — snowball and avalanche strategies.

Deterministic debt payoff calculator that generates month-by-month
payment schedules using two proven strategies:

- **Snowball**: Pay off smallest balances first for psychological wins.
- **Avalanche**: Pay off highest interest rates first to minimize total interest.

CRITICAL: All monetary values use Decimal — NEVER float.
All calculations are deterministic — no LLM, no randomness.
Financial data never leaves the local environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

# ─── Constants ────────────────────────────────────────────────────────────

# Monthly interest calculation precision
_DECIMAL_PLACES = Decimal("0.01")
_MONTHS_PER_YEAR = Decimal("12")

# Safety limit to prevent infinite loops on bad data
_MAX_PAYOFF_MONTHS = 600  # 50 years


# ─── Enums ────────────────────────────────────────────────────────────────


class DebtType(StrEnum):
    """Classification of debt types."""

    CREDIT_CARD = "credit_card"
    STUDENT_LOAN = "student_loan"
    MORTGAGE = "mortgage"
    AUTO_LOAN = "auto_loan"
    PERSONAL_LOAN = "personal_loan"
    MEDICAL = "medical"
    OTHER = "other"


# ─── Data Models ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Debt:
    """A single debt obligation.

    All monetary fields use Decimal for precise financial calculations.

    Parameters
    ----------
    name : str
        Human-readable name for the debt (e.g., "Chase Visa").
    balance : Decimal
        Current outstanding balance. Must be >= 0.
    interest_rate : Decimal
        Annual interest rate as a percentage (e.g., Decimal("19.99") for 19.99%).
        Must be >= 0.
    minimum_payment : Decimal
        Required monthly minimum payment. Must be >= 0.
    debt_type : DebtType
        Classification of the debt.
    """

    name: str
    balance: Decimal
    interest_rate: Decimal
    minimum_payment: Decimal
    debt_type: DebtType = DebtType.OTHER

    def __post_init__(self) -> None:
        """Validate debt fields."""
        if self.balance < Decimal("0"):
            msg = f"Balance must be >= 0, got {self.balance}"
            raise ValueError(msg)
        if self.interest_rate < Decimal("0"):
            msg = f"Interest rate must be >= 0, got {self.interest_rate}"
            raise ValueError(msg)
        if self.minimum_payment < Decimal("0"):
            msg = f"Minimum payment must be >= 0, got {self.minimum_payment}"
            raise ValueError(msg)


@dataclass(frozen=True)
class MonthlyEntry:
    """A single month's payment record in the payoff schedule.

    Parameters
    ----------
    month : int
        Month number (1-based).
    payment : Decimal
        Total payment made this month.
    principal : Decimal
        Amount applied to principal this month.
    interest : Decimal
        Interest charged this month.
    remaining_balance : Decimal
        Balance remaining after this month's payment.
    """

    month: int
    payment: Decimal
    principal: Decimal
    interest: Decimal
    remaining_balance: Decimal


@dataclass(frozen=True)
class PayoffSchedule:
    """Month-by-month payoff schedule for a single debt.

    Parameters
    ----------
    debt_name : str
        Name of the debt this schedule belongs to.
    entries : tuple[MonthlyEntry, ...]
        Ordered monthly payment entries.
    """

    debt_name: str
    entries: tuple[MonthlyEntry, ...]


@dataclass(frozen=True)
class PayoffResult:
    """Complete result from a debt payoff strategy calculation.

    Parameters
    ----------
    strategy_name : str
        Name of the strategy used ("snowball" or "avalanche").
    total_paid : Decimal
        Total amount paid across all debts over the entire schedule.
    total_interest : Decimal
        Total interest paid across all debts.
    months_to_payoff : int
        Number of months to pay off all debts completely.
    monthly_payment : Decimal
        Total monthly payment budget used (sum of all minimums + extra).
    schedules : tuple[PayoffSchedule, ...]
        Per-debt monthly payment schedules.
    """

    strategy_name: str
    total_paid: Decimal
    total_interest: Decimal
    months_to_payoff: int
    monthly_payment: Decimal
    schedules: tuple[PayoffSchedule, ...]


@dataclass(frozen=True)
class StrategyComparison:
    """Side-by-side comparison of snowball vs. avalanche results.

    Parameters
    ----------
    snowball : PayoffResult
        Full snowball strategy result.
    avalanche : PayoffResult
        Full avalanche strategy result.
    interest_savings : Decimal
        How much interest the avalanche saves over snowball.
        Positive means avalanche saves money; zero if identical.
    faster_strategy : str
        Which strategy pays off sooner ("snowball", "avalanche", or "tied").
    months_difference : int
        Difference in months to payoff between strategies.
    """

    snowball: PayoffResult
    avalanche: PayoffResult
    interest_savings: Decimal
    faster_strategy: str
    months_difference: int


# ─── Internal Helpers ─────────────────────────────────────────────────────


def _monthly_interest(balance: Decimal, annual_rate: Decimal) -> Decimal:
    """Calculate one month of interest on a balance.

    Parameters
    ----------
    balance : Decimal
        Current outstanding balance.
    annual_rate : Decimal
        Annual interest rate as a percentage (e.g., 19.99 for 19.99%).

    Returns
    -------
    Decimal
        Interest for one month, rounded to 2 decimal places.
    """
    if annual_rate == Decimal("0"):
        return Decimal("0.00")
    monthly_rate = annual_rate / Decimal("100") / _MONTHS_PER_YEAR
    return (balance * monthly_rate).quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def _calculate_payoff(
    debts: list[Debt],
    extra_payment: Decimal,
    sort_key: str,
) -> PayoffResult:
    """Core payoff engine shared by snowball and avalanche.

    Simulates month-by-month debt payoff with the debt-rollover pattern:
    1. Apply minimum payments to all debts
    2. Apply extra payment to the target debt (per sort order)
    3. When a debt is paid off, roll its payment into the extra pool
    4. Repeat until all debts are paid off

    Parameters
    ----------
    debts : list[Debt]
        List of debts to pay off.
    extra_payment : Decimal
        Extra monthly payment above the sum of all minimums.
    sort_key : str
        "snowball" (sort by balance ascending) or
        "avalanche" (sort by interest_rate descending).

    Returns
    -------
    PayoffResult
        Complete payoff result with schedules.
    """
    if not debts:
        return PayoffResult(
            strategy_name=sort_key,
            total_paid=Decimal("0.00"),
            total_interest=Decimal("0.00"),
            months_to_payoff=0,
            monthly_payment=Decimal("0.00"),
            schedules=(),
        )

    # Filter out zero-balance debts
    active_debts = [d for d in debts if d.balance > Decimal("0")]
    if not active_debts:
        total_min = sum((d.minimum_payment for d in debts), Decimal("0"))
        return PayoffResult(
            strategy_name=sort_key,
            total_paid=Decimal("0.00"),
            total_interest=Decimal("0.00"),
            months_to_payoff=0,
            monthly_payment=total_min + extra_payment,
            schedules=(),
        )

    # Sort debts according to strategy
    if sort_key == "snowball":
        sorted_debts = sorted(active_debts, key=lambda d: (d.balance, d.name))
    else:  # avalanche
        sorted_debts = sorted(active_debts, key=lambda d: (-d.interest_rate, d.balance, d.name))

    # Calculate total monthly payment budget
    total_minimum = sum((d.minimum_payment for d in sorted_debts), Decimal("0"))
    monthly_budget = total_minimum + extra_payment

    # Track state per debt
    balances: dict[str, Decimal] = {d.name: d.balance for d in sorted_debts}
    minimums: dict[str, Decimal] = {d.name: d.minimum_payment for d in sorted_debts}
    rates: dict[str, Decimal] = {d.name: d.interest_rate for d in sorted_debts}
    entries: dict[str, list[MonthlyEntry]] = {d.name: [] for d in sorted_debts}

    month = 0
    total_paid = Decimal("0.00")
    total_interest = Decimal("0.00")

    # Priority order: list of debt names in strategy order
    priority_order = [d.name for d in sorted_debts]

    while any(balances[name] > Decimal("0") for name in priority_order):
        month += 1
        if month > _MAX_PAYOFF_MONTHS:
            break

        # Calculate available extra payment for this month
        # Extra = budget minus minimums of still-active debts
        active_names = [name for name in priority_order if balances[name] > Decimal("0")]
        active_minimums = sum(minimums[name] for name in active_names)
        available_extra = monthly_budget - active_minimums

        # Process each active debt
        for name in active_names:
            balance = balances[name]
            if balance <= Decimal("0"):
                continue

            # Calculate interest
            interest = _monthly_interest(balance, rates[name])
            total_interest += interest
            balance += interest

            # Determine payment for this debt
            payment = minimums[name]

            # First active debt in priority order gets the extra
            if name == active_names[0] and available_extra > Decimal("0"):
                payment += available_extra

            # Cap payment at remaining balance
            if payment > balance:
                payment = balance

            payment = payment.quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)
            principal = (payment - interest).quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)

            # Handle edge case where interest exceeds payment
            if principal < Decimal("0"):
                principal = Decimal("0.00")

            balance = (balance - payment).quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)

            # Prevent tiny negative balances from rounding
            if balance < Decimal("0"):
                balance = Decimal("0.00")

            balances[name] = balance
            total_paid += payment

            entries[name].append(
                MonthlyEntry(
                    month=month,
                    payment=payment,
                    principal=principal,
                    interest=interest,
                    remaining_balance=balance,
                )
            )

    # Build schedules
    schedules = tuple(
        PayoffSchedule(
            debt_name=name,
            entries=tuple(entries[name]),
        )
        for name in priority_order
        if entries[name]
    )

    return PayoffResult(
        strategy_name=sort_key,
        total_paid=total_paid.quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP),
        total_interest=total_interest.quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP),
        months_to_payoff=month,
        monthly_payment=monthly_budget.quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP),
        schedules=schedules,
    )


# ─── Public API ───────────────────────────────────────────────────────────


def calculate_snowball(
    debts: list[Debt],
    extra_payment: Decimal = Decimal("0"),
) -> PayoffResult:
    """Calculate debt payoff using the snowball method.

    The snowball method prioritizes paying off the smallest balance first.
    Once a debt is eliminated, its payment amount rolls into the next
    smallest debt. This builds momentum through quick psychological wins.

    Parameters
    ----------
    debts : list[Debt]
        List of debts to pay off.
    extra_payment : Decimal
        Additional monthly payment above the sum of all minimum payments.
        Defaults to 0 (minimum payments only).

    Returns
    -------
    PayoffResult
        Complete payoff result with strategy="snowball", totals, and
        per-debt monthly schedules.
    """
    return _calculate_payoff(debts, extra_payment, "snowball")


def calculate_avalanche(
    debts: list[Debt],
    extra_payment: Decimal = Decimal("0"),
) -> PayoffResult:
    """Calculate debt payoff using the avalanche method.

    The avalanche method prioritizes paying off the highest interest rate
    first. This minimizes total interest paid over the life of all debts.
    Once a debt is eliminated, its payment rolls into the next highest
    rate debt.

    Parameters
    ----------
    debts : list[Debt]
        List of debts to pay off.
    extra_payment : Decimal
        Additional monthly payment above the sum of all minimum payments.
        Defaults to 0 (minimum payments only).

    Returns
    -------
    PayoffResult
        Complete payoff result with strategy="avalanche", totals, and
        per-debt monthly schedules.
    """
    return _calculate_payoff(debts, extra_payment, "avalanche")


def compare_strategies(
    debts: list[Debt],
    extra_payment: Decimal = Decimal("0"),
) -> StrategyComparison:
    """Compare snowball and avalanche strategies side by side.

    Runs both methods on the same debt portfolio and returns a comparison
    showing total paid, total interest, months to payoff, and the interest
    savings from choosing the better strategy.

    Parameters
    ----------
    debts : list[Debt]
        List of debts to compare strategies on.
    extra_payment : Decimal
        Additional monthly payment above the sum of all minimum payments.
        Defaults to 0 (minimum payments only).

    Returns
    -------
    StrategyComparison
        Side-by-side comparison with interest savings and faster strategy.
    """
    snowball = calculate_snowball(debts, extra_payment)
    avalanche = calculate_avalanche(debts, extra_payment)

    interest_savings = (snowball.total_interest - avalanche.total_interest).quantize(
        _DECIMAL_PLACES, rounding=ROUND_HALF_UP
    )

    if snowball.months_to_payoff < avalanche.months_to_payoff:
        faster = "snowball"
    elif avalanche.months_to_payoff < snowball.months_to_payoff:
        faster = "avalanche"
    else:
        faster = "tied"

    months_diff = abs(snowball.months_to_payoff - avalanche.months_to_payoff)

    return StrategyComparison(
        snowball=snowball,
        avalanche=avalanche,
        interest_savings=interest_savings,
        faster_strategy=faster,
        months_difference=months_diff,
    )
