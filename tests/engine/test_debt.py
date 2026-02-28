"""Tests for the Debt Payoff Engine — snowball, avalanche, comparison.

At least 30 tests covering:
- Data model validation
- Single debt snowball/avalanche (both methods equivalent)
- Multiple debts with known expected outcomes
- 0% interest edge case
- Minimum payment only (no extra)
- Large extra payment (pays off fast)
- Comparison shows avalanche saves more interest
- Comparison shows identical for single debt
- All Decimal precision maintained (no floating-point artifacts)
- Edge cases: zero balance, minimum > balance, empty list
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from alchymine.engine.wealth.debt import (
    Debt,
    DebtType,
    MonthlyEntry,
    PayoffResult,
    PayoffSchedule,
    StrategyComparison,
    calculate_avalanche,
    calculate_snowball,
    compare_strategies,
)

# ═══════════════════════════════════════════════════════════════════════════
# Fixtures / Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _make_debt(
    name: str = "Test Debt",
    balance: str = "1000.00",
    interest_rate: str = "18.00",
    minimum_payment: str = "25.00",
    debt_type: DebtType = DebtType.CREDIT_CARD,
) -> Debt:
    """Helper to create a Debt with string-based Decimals."""
    return Debt(
        name=name,
        balance=Decimal(balance),
        interest_rate=Decimal(interest_rate),
        minimum_payment=Decimal(minimum_payment),
        debt_type=debt_type,
    )


def _standard_two_debts() -> list[Debt]:
    """Two debts where avalanche and snowball differ.

    Debt A: Small balance, low rate.
    Debt B: Large balance, high rate.
    Snowball targets A first; Avalanche targets B first.
    """
    return [
        _make_debt(
            name="Small Balance Low Rate",
            balance="500.00",
            interest_rate="5.00",
            minimum_payment="25.00",
            debt_type=DebtType.PERSONAL_LOAN,
        ),
        _make_debt(
            name="Large Balance High Rate",
            balance="5000.00",
            interest_rate="22.00",
            minimum_payment="100.00",
            debt_type=DebtType.CREDIT_CARD,
        ),
    ]


def _three_debts() -> list[Debt]:
    """Three debts with varied balances and rates."""
    return [
        _make_debt(
            name="Medical Bill",
            balance="800.00",
            interest_rate="0.00",
            minimum_payment="50.00",
            debt_type=DebtType.MEDICAL,
        ),
        _make_debt(
            name="Credit Card",
            balance="3000.00",
            interest_rate="24.99",
            minimum_payment="60.00",
            debt_type=DebtType.CREDIT_CARD,
        ),
        _make_debt(
            name="Auto Loan",
            balance="12000.00",
            interest_rate="6.50",
            minimum_payment="250.00",
            debt_type=DebtType.AUTO_LOAN,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Data Model Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDebtModel:
    """Tests for the Debt data model."""

    def test_create_valid_debt(self) -> None:
        """Creating a debt with valid parameters succeeds."""
        debt = _make_debt()
        assert debt.name == "Test Debt"
        assert debt.balance == Decimal("1000.00")
        assert debt.interest_rate == Decimal("18.00")
        assert debt.minimum_payment == Decimal("25.00")
        assert debt.debt_type == DebtType.CREDIT_CARD

    def test_debt_is_frozen(self) -> None:
        """Debt is immutable (frozen dataclass)."""
        debt = _make_debt()
        with pytest.raises(AttributeError):
            debt.balance = Decimal("500.00")  # type: ignore[misc]

    def test_negative_balance_raises(self) -> None:
        """Negative balance raises ValueError."""
        with pytest.raises(ValueError, match="Balance must be >= 0"):
            _make_debt(balance="-100.00")

    def test_negative_interest_rate_raises(self) -> None:
        """Negative interest rate raises ValueError."""
        with pytest.raises(ValueError, match="Interest rate must be >= 0"):
            _make_debt(interest_rate="-5.00")

    def test_negative_minimum_payment_raises(self) -> None:
        """Negative minimum payment raises ValueError."""
        with pytest.raises(ValueError, match="Minimum payment must be >= 0"):
            _make_debt(minimum_payment="-10.00")

    def test_zero_balance_debt_valid(self) -> None:
        """A debt with zero balance is valid (already paid off)."""
        debt = _make_debt(balance="0.00")
        assert debt.balance == Decimal("0.00")

    def test_debt_type_enum_values(self) -> None:
        """All expected debt types exist."""
        assert DebtType.CREDIT_CARD == "credit_card"
        assert DebtType.STUDENT_LOAN == "student_loan"
        assert DebtType.MORTGAGE == "mortgage"
        assert DebtType.AUTO_LOAN == "auto_loan"
        assert DebtType.PERSONAL_LOAN == "personal_loan"
        assert DebtType.MEDICAL == "medical"
        assert DebtType.OTHER == "other"

    def test_all_values_are_decimal(self) -> None:
        """All monetary fields are Decimal, not float."""
        debt = _make_debt()
        assert isinstance(debt.balance, Decimal)
        assert isinstance(debt.interest_rate, Decimal)
        assert isinstance(debt.minimum_payment, Decimal)


# ═══════════════════════════════════════════════════════════════════════════
# Result Model Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestResultModels:
    """Tests for PayoffResult and related data models."""

    def test_monthly_entry_is_frozen(self) -> None:
        """MonthlyEntry is immutable."""
        entry = MonthlyEntry(
            month=1,
            payment=Decimal("100.00"),
            principal=Decimal("85.00"),
            interest=Decimal("15.00"),
            remaining_balance=Decimal("915.00"),
        )
        with pytest.raises(AttributeError):
            entry.payment = Decimal("200.00")  # type: ignore[misc]

    def test_payoff_schedule_is_frozen(self) -> None:
        """PayoffSchedule is immutable."""
        schedule = PayoffSchedule(debt_name="Test", entries=())
        with pytest.raises(AttributeError):
            schedule.debt_name = "Changed"  # type: ignore[misc]

    def test_payoff_result_is_frozen(self) -> None:
        """PayoffResult is immutable."""
        result = PayoffResult(
            strategy_name="snowball",
            total_paid=Decimal("0.00"),
            total_interest=Decimal("0.00"),
            months_to_payoff=0,
            monthly_payment=Decimal("0.00"),
            schedules=(),
        )
        with pytest.raises(AttributeError):
            result.strategy_name = "changed"  # type: ignore[misc]

    def test_strategy_comparison_is_frozen(self) -> None:
        """StrategyComparison is immutable."""
        result = PayoffResult(
            strategy_name="snowball",
            total_paid=Decimal("0.00"),
            total_interest=Decimal("0.00"),
            months_to_payoff=0,
            monthly_payment=Decimal("0.00"),
            schedules=(),
        )
        comparison = StrategyComparison(
            snowball=result,
            avalanche=result,
            interest_savings=Decimal("0.00"),
            faster_strategy="tied",
            months_difference=0,
        )
        with pytest.raises(AttributeError):
            comparison.faster_strategy = "snowball"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════
# Single Debt Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSingleDebt:
    """Tests for snowball/avalanche with a single debt."""

    def test_single_debt_snowball_returns_result(self) -> None:
        """Snowball with one debt produces a valid PayoffResult."""
        debt = _make_debt(balance="1000.00", interest_rate="12.00", minimum_payment="50.00")
        result = calculate_snowball([debt])
        assert isinstance(result, PayoffResult)
        assert result.strategy_name == "snowball"
        assert result.months_to_payoff > 0
        assert result.total_paid > Decimal("0")

    def test_single_debt_avalanche_returns_result(self) -> None:
        """Avalanche with one debt produces a valid PayoffResult."""
        debt = _make_debt(balance="1000.00", interest_rate="12.00", minimum_payment="50.00")
        result = calculate_avalanche([debt])
        assert isinstance(result, PayoffResult)
        assert result.strategy_name == "avalanche"
        assert result.months_to_payoff > 0

    def test_single_debt_both_methods_identical(self) -> None:
        """With one debt, snowball and avalanche produce identical results."""
        debt = _make_debt(balance="2000.00", interest_rate="15.00", minimum_payment="75.00")
        snowball = calculate_snowball([debt], Decimal("50.00"))
        avalanche = calculate_avalanche([debt], Decimal("50.00"))

        assert snowball.total_paid == avalanche.total_paid
        assert snowball.total_interest == avalanche.total_interest
        assert snowball.months_to_payoff == avalanche.months_to_payoff

    def test_single_debt_schedule_ends_at_zero(self) -> None:
        """The schedule's final entry has remaining_balance == 0."""
        debt = _make_debt(balance="500.00", interest_rate="10.00", minimum_payment="50.00")
        result = calculate_snowball([debt], Decimal("50.00"))
        assert len(result.schedules) == 1
        last_entry = result.schedules[0].entries[-1]
        assert last_entry.remaining_balance == Decimal("0.00")

    def test_single_debt_total_paid_ge_balance(self) -> None:
        """Total paid is at least the original balance (plus interest)."""
        debt = _make_debt(balance="1000.00", interest_rate="18.00", minimum_payment="30.00")
        result = calculate_snowball([debt])
        assert result.total_paid >= Decimal("1000.00")

    def test_single_debt_total_interest_positive_with_rate(self) -> None:
        """A debt with nonzero interest rate accumulates interest > 0."""
        debt = _make_debt(balance="1000.00", interest_rate="18.00", minimum_payment="50.00")
        result = calculate_snowball([debt])
        assert result.total_interest > Decimal("0.00")

    def test_single_debt_schedule_months_match(self) -> None:
        """Schedule entry count matches months_to_payoff."""
        debt = _make_debt(balance="300.00", interest_rate="10.00", minimum_payment="50.00")
        result = calculate_snowball([debt], Decimal("50.00"))
        assert len(result.schedules[0].entries) == result.months_to_payoff


# ═══════════════════════════════════════════════════════════════════════════
# Zero Interest Edge Case
# ═══════════════════════════════════════════════════════════════════════════


class TestZeroInterest:
    """Tests for debts with 0% interest rate."""

    def test_zero_interest_no_interest_charged(self) -> None:
        """A 0% interest debt accumulates zero interest."""
        debt = _make_debt(balance="1000.00", interest_rate="0.00", minimum_payment="100.00")
        result = calculate_snowball([debt])
        assert result.total_interest == Decimal("0.00")

    def test_zero_interest_total_paid_equals_balance(self) -> None:
        """With 0% interest, total paid equals original balance."""
        debt = _make_debt(balance="1000.00", interest_rate="0.00", minimum_payment="100.00")
        result = calculate_snowball([debt])
        assert result.total_paid == Decimal("1000.00")

    def test_zero_interest_exact_months(self) -> None:
        """0% interest, $1000 balance, $100/month = exactly 10 months."""
        debt = _make_debt(balance="1000.00", interest_rate="0.00", minimum_payment="100.00")
        result = calculate_snowball([debt])
        assert result.months_to_payoff == 10

    def test_zero_interest_with_extra_payment(self) -> None:
        """0% interest, $1000 balance, $100 min + $100 extra = 5 months."""
        debt = _make_debt(balance="1000.00", interest_rate="0.00", minimum_payment="100.00")
        result = calculate_snowball([debt], Decimal("100.00"))
        assert result.months_to_payoff == 5
        assert result.total_paid == Decimal("1000.00")

    def test_zero_interest_schedule_entries_all_zero_interest(self) -> None:
        """Every schedule entry has interest == 0 for a 0% debt."""
        debt = _make_debt(balance="500.00", interest_rate="0.00", minimum_payment="100.00")
        result = calculate_snowball([debt])
        for entry in result.schedules[0].entries:
            assert entry.interest == Decimal("0.00")


# ═══════════════════════════════════════════════════════════════════════════
# Minimum Payment Only (No Extra)
# ═══════════════════════════════════════════════════════════════════════════


class TestMinimumPaymentOnly:
    """Tests with extra_payment = 0 (default)."""

    def test_minimum_only_takes_longer(self) -> None:
        """Minimum only takes longer than minimum + extra."""
        debt = _make_debt(balance="2000.00", interest_rate="18.00", minimum_payment="50.00")
        min_only = calculate_snowball([debt])
        with_extra = calculate_snowball([debt], Decimal("100.00"))
        assert min_only.months_to_payoff > with_extra.months_to_payoff

    def test_minimum_only_costs_more_interest(self) -> None:
        """Minimum only pays more total interest than with extra payment."""
        debt = _make_debt(balance="2000.00", interest_rate="18.00", minimum_payment="50.00")
        min_only = calculate_snowball([debt])
        with_extra = calculate_snowball([debt], Decimal("100.00"))
        assert min_only.total_interest > with_extra.total_interest

    def test_minimum_only_monthly_payment_equals_minimum(self) -> None:
        """When extra is 0, monthly_payment equals sum of minimums."""
        debts = _standard_two_debts()
        result = calculate_snowball(debts)
        expected_budget = sum(d.minimum_payment for d in debts)
        assert result.monthly_payment == expected_budget


# ═══════════════════════════════════════════════════════════════════════════
# Large Extra Payment
# ═══════════════════════════════════════════════════════════════════════════


class TestLargeExtraPayment:
    """Tests with a large extra payment that accelerates payoff."""

    def test_large_extra_pays_off_faster(self) -> None:
        """A $500 extra payment significantly reduces payoff time."""
        debt = _make_debt(balance="5000.00", interest_rate="20.00", minimum_payment="100.00")
        small_extra = calculate_snowball([debt], Decimal("0.00"))
        large_extra = calculate_snowball([debt], Decimal("500.00"))
        assert large_extra.months_to_payoff < small_extra.months_to_payoff

    def test_extra_exceeds_balance_pays_in_one_month(self) -> None:
        """If extra + minimum > balance, debt pays off in 1 month."""
        debt = _make_debt(balance="100.00", interest_rate="12.00", minimum_payment="25.00")
        result = calculate_snowball([debt], Decimal("200.00"))
        assert result.months_to_payoff == 1

    def test_large_extra_reduces_total_interest(self) -> None:
        """Large extra payment reduces total interest paid."""
        debt = _make_debt(balance="10000.00", interest_rate="22.00", minimum_payment="200.00")
        small = calculate_snowball([debt], Decimal("0.00"))
        large = calculate_snowball([debt], Decimal("800.00"))
        assert large.total_interest < small.total_interest


# ═══════════════════════════════════════════════════════════════════════════
# Multiple Debts — Snowball vs. Avalanche
# ═══════════════════════════════════════════════════════════════════════════


class TestMultipleDebts:
    """Tests with multiple debts to validate strategy differences."""

    def test_snowball_targets_smallest_balance_first(self) -> None:
        """Snowball pays off the smallest balance debt first."""
        debts = _standard_two_debts()
        result = calculate_snowball(debts, Decimal("100.00"))
        # The small balance debt should be in the first schedule
        # and should have fewer months than the larger debt
        small_schedule = next(
            s for s in result.schedules if s.debt_name == "Small Balance Low Rate"
        )
        large_schedule = next(
            s for s in result.schedules if s.debt_name == "Large Balance High Rate"
        )
        small_last_month = small_schedule.entries[-1].month
        large_last_month = large_schedule.entries[-1].month
        assert small_last_month < large_last_month

    def test_avalanche_targets_highest_rate_first(self) -> None:
        """Avalanche prioritizes the highest interest rate debt."""
        debts = _standard_two_debts()
        result = calculate_avalanche(debts, Decimal("100.00"))
        # The high rate debt gets extra payment, so look at first month
        # High rate debt should get more than its minimum in month 1
        high_rate_schedule = next(
            s for s in result.schedules if s.debt_name == "Large Balance High Rate"
        )
        first_entry = high_rate_schedule.entries[0]
        assert first_entry.payment > Decimal("100.00")  # min is 100, should get extra

    def test_avalanche_saves_interest_over_snowball(self) -> None:
        """Avalanche pays less total interest than snowball with mixed debts."""
        debts = _standard_two_debts()
        extra = Decimal("100.00")
        snowball = calculate_snowball(debts, extra)
        avalanche = calculate_avalanche(debts, extra)
        assert avalanche.total_interest <= snowball.total_interest

    def test_three_debts_snowball_order(self) -> None:
        """Snowball processes three debts in ascending balance order."""
        debts = _three_debts()
        result = calculate_snowball(debts, Decimal("50.00"))
        # Medical ($800) paid off first, then Credit Card ($3000), then Auto ($12000)
        medical = next(s for s in result.schedules if s.debt_name == "Medical Bill")
        cc = next(s for s in result.schedules if s.debt_name == "Credit Card")
        auto = next(s for s in result.schedules if s.debt_name == "Auto Loan")
        assert medical.entries[-1].month < cc.entries[-1].month
        assert cc.entries[-1].month <= auto.entries[-1].month

    def test_three_debts_avalanche_order(self) -> None:
        """Avalanche processes three debts in descending rate order."""
        debts = _three_debts()
        result = calculate_avalanche(debts, Decimal("50.00"))
        # Credit Card (24.99%) gets extra first, then Auto (6.50%), then Medical (0%)
        cc = next(s for s in result.schedules if s.debt_name == "Credit Card")
        # CC should get more than its minimum in month 1
        assert cc.entries[0].payment > Decimal("60.00")

    def test_all_debts_reach_zero_balance(self) -> None:
        """Every debt in a multi-debt payoff ends at zero balance."""
        debts = _three_debts()
        result = calculate_snowball(debts, Decimal("100.00"))
        for schedule in result.schedules:
            last_entry = schedule.entries[-1]
            assert last_entry.remaining_balance == Decimal("0.00")

    def test_avalanche_all_debts_reach_zero(self) -> None:
        """Every debt in avalanche payoff ends at zero balance."""
        debts = _three_debts()
        result = calculate_avalanche(debts, Decimal("100.00"))
        for schedule in result.schedules:
            last_entry = schedule.entries[-1]
            assert last_entry.remaining_balance == Decimal("0.00")


# ═══════════════════════════════════════════════════════════════════════════
# Strategy Comparison Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCompareStrategies:
    """Tests for compare_strategies()."""

    def test_comparison_returns_both_results(self) -> None:
        """Comparison includes both snowball and avalanche results."""
        debts = _standard_two_debts()
        comp = compare_strategies(debts, Decimal("100.00"))
        assert isinstance(comp, StrategyComparison)
        assert comp.snowball.strategy_name == "snowball"
        assert comp.avalanche.strategy_name == "avalanche"

    def test_comparison_interest_savings_positive(self) -> None:
        """Avalanche saves interest over snowball with mixed rate debts."""
        debts = _standard_two_debts()
        comp = compare_strategies(debts, Decimal("100.00"))
        assert comp.interest_savings >= Decimal("0.00")

    def test_comparison_single_debt_tied(self) -> None:
        """Single debt produces tied comparison (both identical)."""
        debt = _make_debt(balance="5000.00", interest_rate="15.00", minimum_payment="100.00")
        comp = compare_strategies([debt], Decimal("50.00"))
        assert comp.interest_savings == Decimal("0.00")
        assert comp.faster_strategy == "tied"
        assert comp.months_difference == 0

    def test_comparison_identifies_faster_strategy(self) -> None:
        """Comparison correctly identifies which strategy is faster."""
        debts = _standard_two_debts()
        comp = compare_strategies(debts, Decimal("100.00"))
        assert comp.faster_strategy in ("snowball", "avalanche", "tied")

    def test_comparison_months_difference_correct(self) -> None:
        """Months difference matches actual payoff difference."""
        debts = _standard_two_debts()
        comp = compare_strategies(debts, Decimal("100.00"))
        expected_diff = abs(comp.snowball.months_to_payoff - comp.avalanche.months_to_payoff)
        assert comp.months_difference == expected_diff


# ═══════════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_debt_list(self) -> None:
        """Empty debt list returns zero result."""
        result = calculate_snowball([])
        assert result.months_to_payoff == 0
        assert result.total_paid == Decimal("0.00")
        assert result.total_interest == Decimal("0.00")
        assert result.schedules == ()

    def test_empty_debt_list_avalanche(self) -> None:
        """Empty debt list returns zero result for avalanche too."""
        result = calculate_avalanche([])
        assert result.months_to_payoff == 0
        assert result.total_paid == Decimal("0.00")

    def test_zero_balance_debt_skipped(self) -> None:
        """A debt with zero balance is filtered out."""
        debts = [
            _make_debt(name="Zero", balance="0.00", minimum_payment="50.00"),
            _make_debt(
                name="Real", balance="500.00", interest_rate="10.00", minimum_payment="50.00"
            ),
        ]
        result = calculate_snowball(debts)
        # Only the non-zero debt should have a schedule
        debt_names = [s.debt_name for s in result.schedules]
        assert "Zero" not in debt_names
        assert "Real" in debt_names

    def test_minimum_payment_exceeds_balance(self) -> None:
        """When minimum payment > balance, pays off in 1 month."""
        debt = _make_debt(balance="20.00", interest_rate="18.00", minimum_payment="50.00")
        result = calculate_snowball([debt])
        assert result.months_to_payoff == 1
        # Total paid should be approximately balance + 1 month interest
        assert result.total_paid <= Decimal("25.00")

    def test_comparison_empty_debts(self) -> None:
        """Comparing empty debt list returns zero comparison."""
        comp = compare_strategies([])
        assert comp.snowball.months_to_payoff == 0
        assert comp.avalanche.months_to_payoff == 0
        assert comp.interest_savings == Decimal("0.00")
        assert comp.faster_strategy == "tied"

    def test_very_small_balance(self) -> None:
        """A very small balance (e.g., $1.00) is handled correctly."""
        debt = _make_debt(balance="1.00", interest_rate="24.00", minimum_payment="25.00")
        result = calculate_snowball([debt])
        assert result.months_to_payoff == 1
        assert result.total_paid <= Decimal("2.00")  # balance + tiny interest


# ═══════════════════════════════════════════════════════════════════════════
# Decimal Precision Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDecimalPrecision:
    """Tests ensuring Decimal precision is maintained throughout."""

    def test_result_values_are_decimal(self) -> None:
        """All monetary values in PayoffResult are Decimal."""
        debt = _make_debt()
        result = calculate_snowball([debt], Decimal("50.00"))
        assert isinstance(result.total_paid, Decimal)
        assert isinstance(result.total_interest, Decimal)
        assert isinstance(result.monthly_payment, Decimal)

    def test_schedule_entries_are_decimal(self) -> None:
        """All monetary values in schedule entries are Decimal."""
        debt = _make_debt()
        result = calculate_snowball([debt], Decimal("50.00"))
        for schedule in result.schedules:
            for entry in schedule.entries:
                assert isinstance(entry.payment, Decimal)
                assert isinstance(entry.principal, Decimal)
                assert isinstance(entry.interest, Decimal)
                assert isinstance(entry.remaining_balance, Decimal)

    def test_no_floating_point_artifacts(self) -> None:
        """Values like 0.1 + 0.2 don't produce 0.30000000000000004."""
        debt = _make_debt(
            balance="100.10",
            interest_rate="0.00",
            minimum_payment="33.37",
        )
        result = calculate_snowball([debt])
        # With 0% interest, total paid should equal exactly the balance
        assert result.total_paid == Decimal("100.10")
        # No entry should have more than 2 decimal places
        for schedule in result.schedules:
            for entry in schedule.entries:
                assert entry.remaining_balance == entry.remaining_balance.quantize(Decimal("0.01"))

    def test_interest_calculation_precision(self) -> None:
        """Interest calculation rounds to 2 decimal places."""
        # $10,000 at 19.99% annual = $10,000 * 0.1999/12 = $166.583... -> $166.58
        debt = _make_debt(
            balance="10000.00",
            interest_rate="19.99",
            minimum_payment="200.00",
        )
        result = calculate_snowball([debt])
        first_entry = result.schedules[0].entries[0]
        assert first_entry.interest == Decimal("166.58")

    def test_comparison_interest_savings_is_decimal(self) -> None:
        """Interest savings in comparison is Decimal, not float."""
        debts = _standard_two_debts()
        comp = compare_strategies(debts, Decimal("100.00"))
        assert isinstance(comp.interest_savings, Decimal)


# ═══════════════════════════════════════════════════════════════════════════
# Determinism Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDeterminism:
    """Tests that calculations are fully deterministic."""

    def test_snowball_deterministic(self) -> None:
        """Same inputs always produce the same snowball result."""
        debts = _standard_two_debts()
        result1 = calculate_snowball(debts, Decimal("100.00"))
        result2 = calculate_snowball(debts, Decimal("100.00"))
        assert result1.total_paid == result2.total_paid
        assert result1.total_interest == result2.total_interest
        assert result1.months_to_payoff == result2.months_to_payoff

    def test_avalanche_deterministic(self) -> None:
        """Same inputs always produce the same avalanche result."""
        debts = _standard_two_debts()
        result1 = calculate_avalanche(debts, Decimal("100.00"))
        result2 = calculate_avalanche(debts, Decimal("100.00"))
        assert result1.total_paid == result2.total_paid
        assert result1.total_interest == result2.total_interest
        assert result1.months_to_payoff == result2.months_to_payoff

    def test_comparison_deterministic(self) -> None:
        """Same inputs always produce the same comparison."""
        debts = _three_debts()
        comp1 = compare_strategies(debts, Decimal("200.00"))
        comp2 = compare_strategies(debts, Decimal("200.00"))
        assert comp1.interest_savings == comp2.interest_savings
        assert comp1.faster_strategy == comp2.faster_strategy
        assert comp1.months_difference == comp2.months_difference


# ═══════════════════════════════════════════════════════════════════════════
# Package Export Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPackageExports:
    """Tests that debt module is properly exported from wealth package."""

    def test_debt_importable_from_wealth(self) -> None:
        """Debt can be imported from alchymine.engine.wealth."""
        from alchymine.engine.wealth import Debt as WealthDebt

        assert WealthDebt is Debt

    def test_calculate_snowball_importable_from_wealth(self) -> None:
        """calculate_snowball can be imported from alchymine.engine.wealth."""
        from alchymine.engine.wealth import calculate_snowball as cs

        assert cs is calculate_snowball

    def test_calculate_avalanche_importable_from_wealth(self) -> None:
        """calculate_avalanche can be imported from alchymine.engine.wealth."""
        from alchymine.engine.wealth import calculate_avalanche as ca

        assert ca is calculate_avalanche

    def test_compare_strategies_importable_from_wealth(self) -> None:
        """compare_strategies can be imported from alchymine.engine.wealth."""
        from alchymine.engine.wealth import compare_strategies as cs

        assert cs is compare_strategies

    def test_all_exports_in_dunder_all(self) -> None:
        """All debt-related symbols are in wealth.__all__."""
        from alchymine.engine.wealth import __all__ as wealth_all

        expected = [
            "Debt",
            "DebtType",
            "MonthlyEntry",
            "PayoffSchedule",
            "PayoffResult",
            "StrategyComparison",
            "calculate_snowball",
            "calculate_avalanche",
            "compare_strategies",
        ]
        for name in expected:
            assert name in wealth_all, f"{name} not in wealth.__all__"
