"""The frozen test runner must reject retries before reading a dataset."""

import pytest
from ml import final_evaluation


def test_reserved_run_refuses_to_read_again(tmp_path, monkeypatch):
    reservation = tmp_path / "reservation"
    reservation.mkdir()
    monkeypatch.setattr(final_evaluation, "OUTPUT", reservation)
    monkeypatch.setattr(
        final_evaluation,
        "prepare_partitions",
        lambda **_: pytest.fail("Dataset must not be loaded again"),
    )
    with pytest.raises(ValueError, match="never rerun"):
        final_evaluation.run()
