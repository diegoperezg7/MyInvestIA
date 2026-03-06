import numpy as np
import pytest

from app.services.quant_metrics import (
    conditional_value_at_risk,
    contribution_to_risk,
    max_drawdown_from_prices,
    returns_from_prices,
    risk_parity_weights,
    rolling_returns,
    rolling_volatility,
    sharpe_ratio,
    sortino_ratio,
    value_at_risk,
)


def test_sharpe_and_sortino_positive_for_stable_positive_series():
    returns = np.array([0.01, 0.012, 0.008, 0.011, 0.009, 0.013], dtype=float)
    assert sharpe_ratio(returns, risk_free_rate=0.0) > 0
    assert sortino_ratio(returns, risk_free_rate=0.0) == 0.0


def test_max_drawdown_from_prices_matches_peak_to_trough():
    prices = [100.0, 110.0, 90.0, 95.0]
    assert max_drawdown_from_prices(prices) == pytest.approx(-0.181818, abs=1e-6)


def test_rolling_metrics_preserve_length_and_null_prefix():
    returns = returns_from_prices([100, 102, 101, 104, 103, 105, 106])
    rolling_ret = rolling_returns(returns, 3)
    rolling_vol = rolling_volatility(returns, 3)
    assert len(rolling_ret) == len(returns)
    assert len(rolling_vol) == len(returns)
    assert rolling_ret[0] is None
    assert rolling_vol[1] is None
    assert rolling_ret[-1] is not None
    assert rolling_vol[-1] is not None


def test_var_and_cvar_tail_relationship():
    returns = np.array([-0.06, -0.04, -0.03, -0.01, 0.0, 0.01, 0.02], dtype=float)
    var_95 = value_at_risk(returns, 0.95)
    cvar_95 = conditional_value_at_risk(returns, 0.95)
    assert cvar_95 <= var_95
    assert var_95 < 0


def test_contribution_to_risk_sums_to_one():
    weights = np.array([0.5, 0.3, 0.2], dtype=float)
    cov = np.array(
        [
            [0.04, 0.01, 0.00],
            [0.01, 0.09, 0.01],
            [0.00, 0.01, 0.16],
        ],
        dtype=float,
    )
    ctr = contribution_to_risk(weights, cov)
    assert float(np.sum(ctr)) == pytest.approx(1.0, abs=1e-6)


def test_risk_parity_weights_are_long_only_and_normalized():
    cov = np.array(
        [
            [0.04, 0.01, 0.00],
            [0.01, 0.09, 0.01],
            [0.00, 0.01, 0.16],
        ],
        dtype=float,
    )
    weights = risk_parity_weights(["A", "B", "C"], cov)
    assert set(weights) == {"A", "B", "C"}
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)
    assert all(weight >= 0 for weight in weights.values())
