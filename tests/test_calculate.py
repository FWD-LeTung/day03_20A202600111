from src.tools.calculate import (
    calculate_simple_interest,
    calculate_compound_interest,
    calculate_early_withdraw,
    calculate_partial_withdraw,
    calculate,
)


def test_simple_interest_12m_12pct():
    interest, total = calculate_simple_interest(amount=100_000_000, rate=12.0, duration=12)
    assert interest == 12_000_000
    assert total == 112_000_000


def test_compound_interest_increases_total():
    interest_s, total_s = calculate_simple_interest(amount=10_000_000, rate=12.0, duration=12)
    interest_c, total_c = calculate_compound_interest(amount=10_000_000, rate=12.0, duration=12, n=12)
    assert total_c > total_s
    assert interest_c > interest_s


def test_early_withdraw_uses_non_term_rate_default():
    interest, total = calculate_early_withdraw(amount=100_000_000, withdraw_time=2, rate=0.2)
    assert interest == 100_000_000 * (0.2 / 100) * (2 / 12)
    assert total == 100_000_000 + interest


def test_partial_withdraw_splits_components():
    out = calculate_partial_withdraw(
        total_amount=100_000_000,
        withdraw_amount=40_000_000,
        withdraw_time=2,
        duration=6,
        rate=6.0,
    )
    assert out["withdraw_part"]["amount"] == 40_000_000
    assert out["remaining_part"]["amount"] == 60_000_000
    assert out["total_interest"] == out["withdraw_part"]["interest"] + out["remaining_part"]["interest"]
    assert out["total_amount"] == out["withdraw_part"]["total"] + out["remaining_part"]["total"]


def test_calculate_wrapper_normal_simple():
    out = calculate(amount=100_000_000, rate=6.0, duration=6, interest_type="simple")
    assert out["type"] == "normal"
    assert out["interest"] == 100_000_000 * (6.0 / 100) * (6 / 12)


def test_calculate_wrapper_early_withdraw():
    out = calculate(amount=100_000_000, rate=6.0, duration=6, withdraw_time=2)
    assert out["type"] == "early_withdraw"

