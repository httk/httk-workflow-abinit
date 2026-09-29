"""``diagnose_abinit`` maps finished calculations to the stable ``abinit.*`` codes."""

from pathlib import Path

from conftest import DATA
from httk.codes.abinit import diagnose_abinit


def _codes(directory: Path, output: str) -> list[tuple[str, str]]:
    return [(item.code, item.severity) for item in diagnose_abinit(directory, output=output)]


def test_a_converged_run_has_no_diagnostics() -> None:
    assert diagnose_abinit(DATA, output="si.abo") == ()


def test_an_unconverged_run_is_an_error() -> None:
    assert _codes(DATA, "si_noconv.abo") == [("abinit.scf_not_converged", "error")]


def test_an_error_block_is_fatal_and_names_the_message() -> None:
    (diagnostic,) = diagnose_abinit(DATA / "error", output="si_err.abo")
    assert (diagnostic.code, diagnostic.severity, diagnostic.source) == ("abinit.error", "fatal", "si_err.abo")
    assert "NOTAVARIABLE" in diagnostic.summary


def test_a_truncated_or_missing_output_is_incomplete(tmp_path: Path) -> None:
    text = (DATA / "si.abo").read_text(encoding="utf-8")
    (tmp_path / "run.abo").write_text(text[: len(text) // 2], encoding="utf-8")
    assert _codes(tmp_path, "run.abo") == [("abinit.incomplete", "error")]
    assert _codes(tmp_path, "absent.abo") == [("abinit.incomplete", "error")]
