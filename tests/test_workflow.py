"""The ``abinit.scf`` runner refuses invalid input options before starting ABINIT."""

from pathlib import Path

import pytest

from conftest import DATA, SILICON_POSCAR

pytestmark = pytest.mark.slow


@pytest.mark.parametrize("parameters", [{"ecut_ha": 0}, {"kpoints": [2, 0, 2]}, {"kpoints": [2, 2]}])
def test_invalid_input_options_fail_as_input_invalid(
    tmp_path: Path, installed_plugin: None, parameters: dict[str, object]
) -> None:
    pytest.importorskip("httk.atomistic")
    from httk.workflow import TaskManager, Workspace
    from httk.workflow.collecting import job_records
    from httk.workflow.scaffold import new_job

    workspace = Workspace.initialize(tmp_path / "workspace")
    # Never started: the input is refused first.
    workspace.set_setting("abinit.command", str(tmp_path / "no-abinit"))
    (tmp_path / "POSCAR").write_text(SILICON_POSCAR, encoding="utf-8")
    job = new_job(
        workspace,
        "abinit.scf",
        inputs={"structure": tmp_path / "POSCAR"},
        files={"Si.psp8": DATA / "Si.psp8"},
        parameters={"pseudopotentials": {"Si": "Si.psp8"}, **parameters},
        install=True,
    )
    with TaskManager(workspace, heartbeat_interval=0.01) as manager:
        manager.run_until_idle(timeout=120.0)
    [record] = job_records(workspace, states=("succeeded", "failed"))
    assert (record.job_id, record.state) == (job.job_id, "failed")
    assert record.failure is not None and record.failure.code == "abinit.input_invalid", record.failure
