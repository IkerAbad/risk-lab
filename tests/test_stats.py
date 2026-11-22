import numpy as np
import pytest

from risk_lab.stats import christoffersen_independence, kupiec_pof


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
