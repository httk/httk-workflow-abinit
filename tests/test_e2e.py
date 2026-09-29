"""End to end with the real ``abinit``: install, run, and collect the ``abinit.scf`` workflow.

Runs only with a real ``abinit`` (``HTTK_TEST_ABINIT_COMMAND`` or ``abinit`` on PATH).
The workflow is installed as the ``httk_plugin.toml`` plugin of this repository,
as ``httk plugin install`` does, into the test's isolated data home.
"""

import json
import shlex
from pathlib import Path
from typing import Any

import pytest

from conftest import DATA, SILICON_POSCAR, abinit_command, requires_abinit

pytestmark = [requires_abinit, pytest.mark.slow]


def test_abinit_scf_runs_abinit_and_collects_the_total_energy(
    tmp_path: Path, installed_plugin: None, capsys: pytest.CaptureFixture[str]
) -> None:
    pytest.importorskip("httk.atomistic")
    store = pytest.importorskip("httk.store")
    from httk.core import DataRecord, Run
    from httk.core.cli import CLIContext
    from httk.workflow import TaskManager, Workspace
    from httk.workflow.registry import register_workspace
    from httk.workflow.scaffold import new_job
    from httk.workflow.workflow_cli import command

    workspace = Workspace.initialize(tmp_path / "workspace")
    workspace.set_setting("abinit.command", shlex.join(abinit_command() or ()))
    (tmp_path / "POSCAR").write_text(SILICON_POSCAR, encoding="utf-8")
    job = new_job(
        workspace,
        "abinit.scf",
        inputs={"structure": tmp_path / "POSCAR"},
        files={"Si.psp8": DATA / "Si.psp8"},
        parameters={"pseudopotentials": {"Si": "Si.psp8"}, "ecut_ha": 8, "kpoints": [2, 2, 2]},
    )
    with TaskManager(workspace, heartbeat_interval=0.01) as manager:
        manager.run_until_idle(timeout=600.0)
    marker = workspace.find_marker_by_id(job.job_id)
    assert marker is not None
    assert marker.kind == "succeeded", workspace.read_state(marker).get("failure")

    register_workspace("abinit", str(workspace.root))
    database = tmp_path / "results.sqlite"
    arguments = [
        "collect",
        "--workspace",
        "abinit",
        "--into",
        str(database),
        "--id-base",
        "httk.test",
        "--no-id-ledger",
    ]
    assert command(arguments, CLIContext("httk", tmp_path)) == 0
    report = json.loads(capsys.readouterr().out.splitlines()[0])
    assert set(report["outputs"]) == {"total_energy"} and report["stored"]["run"]

    with store.Backend.sqlite(database) as backend:
        searcher = store.SqlStore(backend).searcher()
        energies: list[Any] = [row.energy for row in searcher.results(energy=searcher.variable(DataRecord))]
        searcher = store.SqlStore(backend).searcher()
        runs = list(searcher.results(run=searcher.variable(Run)))
    assert [energy.value for energy in energies] == [pytest.approx(-211.725, abs=0.05)]
    assert len(runs) == 1
