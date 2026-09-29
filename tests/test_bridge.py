"""The ``abinit-*`` bridge commands and the Bash API that forwards to them.

Code verbs need no attempt, so they run straight through the shell bridge.
Stderr is not asserted empty: a sibling code distribution installed in the same
environment may report itself unavailable there.
"""

import json
import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest

from conftest import DATA, SILICON_POSCAR


def _bridge(cwd: Path, *arguments: str) -> "subprocess.CompletedProcess[str]":
    environment = {name: value for name, value in os.environ.items() if not name.startswith("HTTK_WORKFLOW_")}
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "httk.workflow._shell_bridge", *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_energy_and_convergence_answers_and_absences(tmp_path: Path) -> None:
    energy = _bridge(tmp_path, "abinit-energy", "--output", str(DATA / "si.abo"))
    assert (energy.returncode, energy.stdout) == (0, "-7.7807515461\n")
    in_ev = _bridge(tmp_path, "abinit-energy", "--output", str(DATA / "si.abo"), "--unit", "ev")
    assert float(in_ev.stdout) == pytest.approx(-211.7250, abs=1e-3)
    assert _bridge(tmp_path, "abinit-converged", "--output", str(DATA / "si.abo")).returncode == 0
    for verb in ("abinit-energy", "abinit-converged"):
        absent = _bridge(tmp_path, verb, "--output", str(DATA / "si_noconv.abo"))
        assert (absent.returncode, absent.stdout) == (1, "")
    refused = _bridge(tmp_path, "abinit-energy", "--output", str(tmp_path / "missing.abo"))
    assert refused.returncode == 2


def test_diagnose_prints_codes_and_json(tmp_path: Path) -> None:
    clean = _bridge(tmp_path, "abinit-diagnose", "--output", str(DATA / "si.abo"))
    assert (clean.returncode, clean.stdout) == (0, "")
    error = _bridge(tmp_path, "abinit-diagnose", "--output", str(DATA / "error" / "si_err.abo"), "--json")
    assert error.returncode == 20
    assert [item["code"] for item in json.loads(error.stdout)] == ["abinit.error"]


def test_write_input_then_run_with_a_replayed_abinit(tmp_path: Path) -> None:
    pytest.importorskip("httk.atomistic")
    (tmp_path / "POSCAR").write_text(SILICON_POSCAR, encoding="utf-8")
    options = {"structure": "POSCAR", "pseudopotentials": {"Si": "Si.psp8"}, "ecut_ha": 8, "kpoints": [2, 2, 2]}
    (tmp_path / "options.json").write_text(json.dumps(options), encoding="utf-8")
    assert _bridge(tmp_path, "abinit-write-input", "--options", "options.json").returncode == 0
    assert "ngkpt 2 2 2\n" in (tmp_path / "run.abi").read_text(encoding="utf-8")

    replay = "import shutil, sys; shutil.copy(sys.argv[1], 'run.abo')"
    ran = _bridge(tmp_path, "abinit-run", "--", sys.executable, "-c", replay, str(DATA / "si_noconv.abo"))
    assert (ran.returncode, ran.stdout) == (21, "abinit-run-report.json\n")
    report = json.loads((tmp_path / "abinit-run-report.json").read_text(encoding="utf-8"))
    assert report["classification"] == "nonconverged"


def test_the_bash_api_forwards_to_the_bridge(tmp_path: Path) -> None:
    workflow_api = files("httk.workflow").joinpath("languages", "bash", "httk-workflow.sh")
    abinit_api = files("httk.codes.abinit").joinpath("httk-abinit.sh")
    script = (
        f'source "{workflow_api}"; source "{abinit_api}"; httk_abinit_energy --output "{DATA / "si.abo"}" --unit ha'
    )
    environment = {name: value for name, value in os.environ.items() if not name.startswith("HTTK_WORKFLOW_")}
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    environment["HTTK_WORKFLOW_PYTHON"] = sys.executable
    result = subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, env=environment, text=True, capture_output=True, check=False
    )
    assert (result.returncode, result.stdout) == (0, "-7.7807515461\n"), result.stderr
    unguarded = subprocess.run(
        ["bash", "-c", f'source "{abinit_api}"; httk_abinit_energy'], text=True, capture_output=True, check=False
    )
    assert unguarded.returncode == 2 and "source HTTK_WORKFLOW_BASH_API" in unguarded.stderr
