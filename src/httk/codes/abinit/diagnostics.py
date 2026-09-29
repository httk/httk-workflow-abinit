"""Classify a finished ABINIT calculation into stable diagnostics."""

import os
from pathlib import Path

from httk.workflow.codes import Diagnostic

from .outputs import _parse, _read

__all__ = ["diagnose_abinit"]


def diagnose_abinit(directory: str | os.PathLike[str] = ".", *, output: str = "run.abo") -> tuple[Diagnostic, ...]:
    """Diagnose an ABINIT calculation from its main output.

    The codes are stable: ``abinit.error`` (fatal; ABINIT stopped with a
    ``--- !ERROR`` or ``--- !BUG`` block), ``abinit.scf_not_converged`` (error;
    the last SCF cycle ran out of ``nstep``), and ``abinit.incomplete`` (error;
    no ``Calculation completed.`` and no error block, e.g. a killed process). A
    converged, completed run has none. A missing output file is diagnosed like
    an empty one.

    :param directory: Read the calculation files from this directory.
    :param output: The name of the ABINIT main output (``.abo``) in *directory*.
    :return: The diagnostics, empty for a clean run.
    """

    result = _parse(_read(Path(directory) / output))
    diagnostics: list[Diagnostic] = []
    if result.errors:
        diagnostics.append(Diagnostic("abinit.error", "fatal", result.errors[0], output, "\n".join(result.errors)))
    elif not result.completed:
        diagnostics.append(
            Diagnostic("abinit.incomplete", "error", f"{output} has no Calculation completed. line", output)
        )
    if result.converged is False:
        diagnostics.append(
            Diagnostic(
                "abinit.scf_not_converged",
                "error",
                f"nstep={result.scf_steps} was not enough SCF cycles to converge",
                output,
            )
        )
    return tuple(diagnostics)
