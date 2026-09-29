"""``run_abinit`` classifies a supervised run and writes its report.

A stand-in ``abinit`` replays a captured main output, so the classification is
exercised without a real ``abinit``.
"""

import json
import sys
from pathlib import Path

import pytest

from conftest import DATA
from httk.codes.abinit import run_abinit

# Copies the named captured output to the .abo ABINIT would write for the input
# run_abinit appends (``run.abi`` -> ``run.abo``), and exits with a code.
_REPLAY = "import shutil, sys; shutil.copy(sys.argv[1], sys.argv[3].rsplit('.', 1)[0] + '.abo'); print('log'); sys.exit(int(sys.argv[2]))"


def _replay(output: str, code: int = 0) -> list[str]:
    return [sys.executable, "-c", _REPLAY, str(DATA / output), str(code)]


@pytest.mark.parametrize(
    ("argv", "classification"),
    [
        (_replay("si.abo"), "completed"),
        (_replay("si_noconv.abo"), "nonconverged"),
        (_replay("error/si_err.abo", 13), "crashed"),
        (_replay("si.abo", 3), "process_failure"),
    ],
)
def test_the_run_is_classified_and_reported(tmp_path: Path, argv: list[str], classification: str) -> None:
    report = run_abinit(argv, directory=tmp_path)
    assert report.classification == classification
    assert report.ok == (classification == "completed")
    assert report.process.argv[-1] == "run.abi"
    assert (tmp_path / "abinit.log").read_text(encoding="utf-8") == "log\n"
    saved = json.loads((tmp_path / "abinit-run-report.json").read_text(encoding="utf-8"))
    assert saved["format"] == "httk-abinit-run-report" and saved["classification"] == classification
    if classification == "completed":
        assert saved["result"]["total_energy_ha"] == -7.7807515461
        assert report.diagnostics == ()


def test_a_stale_main_output_is_removed_before_the_run(tmp_path: Path) -> None:
    # ABINIT would write run.abo0001 beside a stale run.abo; a run that writes nothing
    # must not be read as the stale converged one.
    (tmp_path / "run.abo").write_text((DATA / "si.abo").read_text(encoding="utf-8"), encoding="utf-8")
    report = run_abinit([sys.executable, "-c", "pass"], directory=tmp_path)
    assert report.classification == "process_failure"
    assert [item.code for item in report.diagnostics] == ["abinit.incomplete"]
