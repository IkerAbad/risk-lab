import numpy as np
import pytest

from risk_lab.stats import (
    block_bootstrap_mean_ci,
    christoffersen_conditional_coverage,
    christoffersen_independence,
    diebold_mariano,
    holm_bonferroni,
    kupiec_pof,
    quantile_loss,
)


def test_kupiec_known_case_matches_expected_p_value():
    # N = 250, x = 10, p0 = 0.05.
    # LR = 0.5633529100175991 and the chi-square(1) p-value is
    # 0.4529124499351952. The p-value is hardcoded to 1e-6.
    result = kupiec_pof(10, 250, 0.05)
    assert result.statistic == pytest.approx(0.5633529100175991, abs=1e-9)
    assert result.p_value == pytest.approx(0.4529124499351952, abs=1e-6)
    assert result.df == 1
    assert result.valid


def test_kupiec_accepts_a_binary_sequence():
    sequence = np.array([1] * 10 + [0] * 240)
    from_sequence = kupiec_pof(sequence, p0=0.05)
    from_count = kupiec_pof(10, 250, 0.05)
    assert from_sequence.statistic == pytest.approx(from_count.statistic)
    assert from_sequence.p_value == pytest.approx(from_count.p_value)


def test_kupiec_zero_violations_limit():
    result = kupiec_pof(0, 250, 0.05)
    expected = -2.0 * 250 * np.log(0.95)
    assert result.statistic == pytest.approx(expected)
    assert result.p_value < 0.001


def test_kupiec_all_violations_limit():
    result = kupiec_pof(250, 250, 0.05)
    expected = -2.0 * 250 * np.log(0.05)
    assert result.statistic == pytest.approx(expected)
    assert result.p_value < 0.001


def test_christoffersen_known_case_matches_expected_p_value():
    # Sequence 0,1,1,0,1,0,0,1 gives n00=1, n01=3, n10=2, n11=1.
    # LR = 1.2429472990872608 and the chi-square(1) p-value is
    # 0.2649037925655114.
    sequence = [0, 1, 1, 0, 1, 0, 0, 1]
    result = christoffersen_independence(sequence)
    assert result.statistic == pytest.approx(1.2429472990872608, abs=1e-9)
    assert result.p_value == pytest.approx(0.2649037925655114, abs=1e-6)
    assert result.df == 1
    assert result.valid


def test_christoffersen_detects_clustering():
    sequence = np.array([0] * 100 + [1] * 50)
    result = christoffersen_independence(sequence)
    assert result.valid
    assert result.p_value < 1e-6


def test_conditional_coverage_known_case():
    # Sequence 0,1,1,0,1,0,0,1: LR_uc = 13.285849654573207 and
    # LR_ind = 1.2429472990872608. The joint statistic is 14.528796953660468
    # with two degrees of freedom and p = 0.0007000222226161839.
    sequence = [0, 1, 1, 0, 1, 0, 0, 1]
    result = christoffersen_conditional_coverage(sequence, p0=0.05)
    assert result.statistic == pytest.approx(14.528796953660468, abs=1e-9)
    assert result.p_value == pytest.approx(0.0007000222226161839, abs=1e-6)
    assert result.df == 2
    assert result.valid


def test_conditional_coverage_is_undefined_without_both_states():
    result = christoffersen_conditional_coverage([0] * 50, p0=0.05)
    assert not result.valid
    assert np.isnan(result.p_value)


def test_christoffersen_is_undefined_without_both_states():
    result = christoffersen_independence([0] * 50)
    assert not result.valid
    assert np.isnan(result.p_value)

    result = christoffersen_independence([1] * 50)
    assert not result.valid
    assert np.isnan(result.p_value)


def test_invalid_inputs_raise():
    with pytest.raises(ValueError, match="between 0 and 1"):
        kupiec_pof(10, 250, 0.0)
    with pytest.raises(ValueError, match="between 0 and n"):
        kupiec_pof(251, 250, 0.05)
    with pytest.raises(ValueError, match="0 and 1"):
        christoffersen_independence([0, 1, 2])
    with pytest.raises(ValueError, match="at least two"):
        christoffersen_independence([0])


def test_kupiec_requires_n_when_given_a_count():
    with pytest.raises(ValueError, match="n must be supplied"):
        kupiec_pof(5)


def test_kupiec_rejects_zero_n():
    with pytest.raises(ValueError, match="n must be positive"):
        kupiec_pof(0, 0, 0.05)


def test_kupiec_rejects_count_and_sequence_together():
    with pytest.raises(ValueError, match="either a count or a sequence"):
        kupiec_pof(np.array([0, 1]), 2, 0.05)


def test_kupiec_rejects_negative_count():
    with pytest.raises(ValueError, match="between 0 and n"):
        kupiec_pof(-1, 10, 0.05)


def test_violations_must_be_one_dimensional():
    with pytest.raises(ValueError, match="one-dimensional"):
        christoffersen_independence(np.array([[0, 1], [1, 0]]))


def test_christoffersen_rejects_a_non_finite_statistic(monkeypatch):
    monkeypatch.setattr("risk_lab.stats.xlogy", lambda *args: np.nan)
    result = christoffersen_independence([0, 1, 0, 1])
    assert not result.valid
    assert np.isnan(result.p_value)
    assert "not finite" in result.note


def test_conditional_coverage_rejects_invalid_p0():
    with pytest.raises(ValueError, match="between 0 and 1"):
        christoffersen_conditional_coverage([0, 1], p0=0.0)


def test_quantile_loss_hand_case():
    returns = np.array([0.01, -0.02, 0.03])
    var_forecasts = np.array([0.05, 0.01, 0.05])
    losses = quantile_loss(returns, var_forecasts, 0.95)
    assert losses == pytest.approx([0.003, 0.0095, 0.004])


def test_quantile_loss_validation():
    with pytest.raises(ValueError, match="one-dimensional"):
        quantile_loss(np.ones((2, 2)), np.ones((2, 2)))
    with pytest.raises(ValueError, match="same length"):
        quantile_loss(np.ones(2), np.ones(3))
    with pytest.raises(ValueError, match="at least two"):
        quantile_loss([0.01], [0.02])
    with pytest.raises(ValueError, match="finite"):
        quantile_loss([0.01, np.nan], [0.02, 0.02])
    with pytest.raises(ValueError, match="between 0 and 1"):
        quantile_loss([0.01, 0.02], [0.02, 0.02], 1.0)


def test_diebold_mariano_identical_losses():
    losses = np.linspace(0.01, 0.02, 100)
    result = diebold_mariano(losses, losses)
    assert result.statistic == 0.0
    assert result.p_value == 1.0
    assert result.mean_difference == 0.0


def test_diebold_mariano_detects_a_lower_loss():
    base = np.linspace(0.01, 0.02, 100)
    better = base - 0.001 + 0.0001 * np.sin(np.arange(100))
    result = diebold_mariano(better, base, lags=5)
    assert result.mean_difference < 0
    assert result.statistic < 0
    assert result.p_value < 0.05


def test_diebold_mariano_validation():
    losses = np.linspace(0.01, 0.02, 100)
    with pytest.raises(ValueError, match="one-dimensional"):
        diebold_mariano(np.ones((2, 2)), np.ones((2, 2)))
    with pytest.raises(ValueError, match="same length"):
        diebold_mariano(np.ones(2), np.ones(3))
    with pytest.raises(ValueError, match="at least two"):
        diebold_mariano([0.01], [0.02])
    with pytest.raises(ValueError, match="finite"):
        diebold_mariano(np.r_[losses[:-1], np.nan], losses)
    with pytest.raises(ValueError, match="non-negative integer"):
        diebold_mariano(losses, losses, lags=-1)
    with pytest.raises(ValueError, match="longer than lags"):
        diebold_mariano(np.ones(3), np.ones(3), lags=5)
    with pytest.raises(ValueError, match="long-run variance"):
        diebold_mariano(np.ones(3), np.zeros(3), lags=0)


def test_holm_bonferroni_known_case():
    adjusted = holm_bonferroni([0.01, 0.04, 0.03, 0.002])
    assert adjusted == pytest.approx([0.03, 0.06, 0.06, 0.008])


def test_holm_bonferroni_validation():
    with pytest.raises(ValueError, match="non-empty"):
        holm_bonferroni([])
    with pytest.raises(ValueError, match="one-dimensional"):
        holm_bonferroni(np.ones((2, 2)))
    with pytest.raises(ValueError, match="finite"):
        holm_bonferroni([0.1, np.nan])
    with pytest.raises(ValueError, match="between 0 and 1"):
        holm_bonferroni([0.1, 1.5])


def test_block_bootstrap_mean_ci_contains_the_mean_and_is_reproducible():
    values = np.arange(100, dtype=float)
    first = block_bootstrap_mean_ci(
        values,
        block_length=10,
        n_boot=200,
        seed=1,
    )
    second = block_bootstrap_mean_ci(
        values,
        block_length=10,
        n_boot=200,
        seed=1,
    )
    assert first == second
    assert first[0] <= values.mean() <= first[1]
    assert first[0] < first[1]


def test_block_bootstrap_mean_ci_validation():
    values = np.arange(100, dtype=float)
    with pytest.raises(ValueError, match="one-dimensional"):
        block_bootstrap_mean_ci(np.ones((2, 2)))
    with pytest.raises(ValueError, match="two values"):
        block_bootstrap_mean_ci([1.0])
    with pytest.raises(ValueError, match="finite"):
        block_bootstrap_mean_ci([1.0, np.nan])
    with pytest.raises(ValueError, match="block_length"):
        block_bootstrap_mean_ci(values, block_length=0)
    with pytest.raises(ValueError, match="block_length"):
        block_bootstrap_mean_ci(values, block_length=101)
    with pytest.raises(ValueError, match="block_length must be an integer"):
        block_bootstrap_mean_ci(values, block_length=10.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="n_boot"):
        block_bootstrap_mean_ci(values, n_boot=0)
    with pytest.raises(ValueError, match="confidence"):
        block_bootstrap_mean_ci(values, confidence=1.0)
