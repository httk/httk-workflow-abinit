"""``parse_abinit_output`` reads real captured ABINIT 10.0.3 output."""

from pathlib import Path

import pytest

from conftest import DATA
from httk.codes.abinit import HA_TO_EV, parse_abinit_output


def test_a_converged_scf_run() -> None:
    result = parse_abinit_output(DATA / "si.abo")
    # The etotal of the final -outvars: echo, more digits than "Etot = -7.780752E+00 Ha" in the log.
    assert result.total_energy_ha == -7.7807515461
    assert result.total_energy_ev == pytest.approx(-7.7807515461 * HA_TO_EV)
    assert (result.converged, result.scf_steps, result.completed, result.errors) == (True, 6, True, ())


def test_an_scf_run_that_stopped_unconverged() -> None:
    result = parse_abinit_output(DATA / "si_noconv.abo")
    # ABINIT still echoes an etotal; an unconverged energy is not reported.
    assert result.total_energy_ha is None and result.total_energy_ev is None
    assert (result.converged, result.scf_steps, result.completed, result.errors) == (False, 1, True, ())


def test_an_error_block_is_read_once_with_its_source_file() -> None:
    result = parse_abinit_output(DATA / "error" / "si_err.abo")
    assert (result.total_energy_ha, result.converged, result.completed) == (None, None, False)
    assert len(result.errors) == 1
    assert result.errors[0].startswith("m_parser.F90: Found token: `NOTAVARIABLE` in the input file.")


def test_a_bug_block_is_an_error_too(tmp_path: Path) -> None:
    text = (DATA / "error" / "si_err.abo").read_text(encoding="utf-8")
    (tmp_path / "run.abo").write_text(text.replace("--- !ERROR", "--- !BUG"), encoding="utf-8")
    assert parse_abinit_output(tmp_path / "run.abo").errors[0].startswith("m_parser.F90: Found token")


@pytest.mark.parametrize(
    ("tolerance", "steps", "line"),
    [
        ("tolvrs", 7, "vres2   =  8.18E-11 < tolvrs=  1.00E-10 =>converged."),
        ("toldff", 3, "At SCF step    3, forces are converged :"),
        ("tolwfr", 11, "max residual=  9.92E-15 < tolwfr=  1.00E-14 =>converged."),
        ("tolrff", 8, "At SCF step    8, forces are sufficiently converged :"),
    ],
)
def test_every_scf_tolerance_wording_counts_as_converged(tolerance: str, steps: int, line: str) -> None:
    path = DATA / "tolerances" / f"si_{tolerance}.abo"
    assert line in path.read_text(encoding="utf-8")
    result = parse_abinit_output(path)
    assert (result.converged, result.scf_steps, result.completed, result.errors) == (True, steps, True, ())
    assert result.total_energy_ha == pytest.approx(-7.78075, abs=1e-4)
