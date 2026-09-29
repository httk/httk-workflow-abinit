#!/usr/bin/env python3
"""abinit.scf: one ABINIT SCF calculation of one structure.

The single ``run`` step stages the structure (the ``structure`` input, staged
as ``files/POSCAR``) and the pseudopotentials named by the ``pseudopotentials``
parameter, writes ``run.abi``, runs ABINIT under supervision, and fails with
the first diagnostic code (``abinit.error``, ``abinit.scf_not_converged``, ...)
when the calculation is not clean.

Settings, resolved job parameter -> ``HTTK_*`` variable -> workspace setting:

* ``abinit.command``: the command that starts ABINIT (default ``abinit``), e.g.
  ``mpirun -np 4 abinit``;
* ``abinit.pseudo_dir``: the directory holding the pseudopotential files
  (default: this job's ``files/``).
"""

import shlex
import shutil
from pathlib import Path
from typing import cast

from httk.workflow import Attempt, Runner

from httk.codes.abinit import run_abinit, write_abinit_input

run = Runner("abinit.scf")


@run.step(name="run")
def run_step(a: Attempt) -> None:
    """Prepare and run ABINIT, then succeed or fail with what was diagnosed."""

    pseudopotentials = a.parameter("pseudopotentials", None)
    if not isinstance(pseudopotentials, dict) or not pseudopotentials:
        a.fail("abinit.input_missing", 'give the job a pseudopotentials parameter, e.g. {"Si": "Si.psp8"}')
        return
    pseudo_dir = Path(str(a.setting("abinit.pseudo_dir", None) or a.payload / "files"))
    for name in pseudopotentials.values():
        if not (pseudo_dir / name).is_file():
            a.fail("abinit.input_missing", f"pseudopotential {name} is not in {pseudo_dir}")
            return
        shutil.copyfile(pseudo_dir / name, a.workdir / name)
    shutil.copyfile(a.payload / "files" / "POSCAR", a.workdir / "POSCAR")
    try:
        nx, ny, nz = (int(n) for n in cast(list[int], a.parameter("kpoints", [4, 4, 4])))
        write_abinit_input(
            a.workdir / "run.abi",
            structure=a.workdir / "POSCAR",
            pseudopotentials=pseudopotentials,
            ecut_ha=float(cast(float, a.parameter("ecut_ha", 15))),
            kpoints=(nx, ny, nz),
        )
    except ValueError as exception:
        a.fail("abinit.input_invalid", str(exception))
        return
    try:
        report = run_abinit(shlex.split(str(a.setting("abinit.command", "abinit"))), directory=a.workdir)
    except OSError as exception:
        a.fail("abinit.failed", f"could not start abinit: {exception}")
        return
    if not report.ok:
        first = report.diagnostics[0] if report.diagnostics else None
        code = first.code if first else f"abinit.{report.classification}"
        a.fail(code, first.summary if first else f"abinit {report.classification}")
        return
    a.state.merge({"total_energy_ha": report.result.total_energy_ha})
    a.succeed()


if __name__ == "__main__":
    raise SystemExit(run.main())
