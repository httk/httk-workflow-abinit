"""Supervised ABINIT execution and its classified run report."""

import dataclasses
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from httk.workflow.codes import Diagnostic, ProcessReport, ProcessSupervisor, launch_command, write_json_atomic

from .diagnostics import diagnose_abinit
from .outputs import AbinitResult, _parse, _read

__all__ = ["AbinitRunReport", "run_abinit"]


@dataclass(frozen=True)
class AbinitRunReport:
    """Classified result of one supervised ABINIT execution.

    The classification is one of ``completed``, ``crashed`` (a ``abinit.error``
    diagnostic), ``nonconverged``, ``process_failure`` (a nonzero exit or an
    incomplete output) and ``timeout``.

    :param process: The supervised process result.
    :param classification: The final run classification.
    :param diagnostics: The diagnostics of the finished calculation.
    :param result: What the ABINIT output says.
    """

    process: ProcessReport
    classification: str
    diagnostics: tuple[Diagnostic, ...]
    result: AbinitResult

    @property
    def ok(self) -> bool:
        """Whether the calculation completed cleanly and converged."""
        return self.classification == "completed"

    def as_mapping(self) -> dict[str, object]:
        """Serialize the report for JSON storage.

        :return: The JSON-compatible report mapping.
        """
        return {
            "format": "httk-abinit-run-report",
            "format_version": 1,
            "process": self.process.as_mapping(),
            "classification": self.classification,
            "diagnostics": [item.as_mapping() for item in self.diagnostics],
            "result": {**dataclasses.asdict(self.result), "errors": list(self.result.errors)},
        }

    def write(self, path: str | os.PathLike[str]) -> Path:
        """Write the report as JSON.

        :param path: Write the report to this path.
        :return: The report path.
        """
        destination = Path(path)
        write_json_atomic(destination, self.as_mapping())
        return destination


def run_abinit(
    argv: Sequence[str],
    *,
    directory: str | os.PathLike[str] = ".",
    input_file: str = "run.abi",
    log_file: str = "abinit.log",
    timeout: float | None = None,
    launch: bool | None = None,
    termination_grace: float = 10.0,
    report_path: str | os.PathLike[str] = "abinit-run-report.json",
) -> AbinitRunReport:
    """Run ABINIT under supervision and write a classified report.

    *argv* names the program (for example ``["abinit"]``); *input_file* is appended to it, the ABINIT 10
    ``abinit run.abi`` invocation. ABINIT names its main output after the input,
    ``<input stem>.abo`` (``run.abo``), and that is the file parsed; an input
    that sets ``output_file`` itself is not supported. Standard output (ABINIT's
    log) goes to *log_file* and standard error beside it with the suffix
    ``.err``. A main output left by an earlier run is removed first: ABINIT
    would otherwise write ``run.abo0001`` and leave the stale ``run.abo`` to be
    mistaken for this run's.

    The attempt's launch prefix (the parallel start, ``HTTK_WORKFLOW_LAUNCH``) is prepended by default;
    ``launch=False`` runs *argv* as given, and a command that already starts with a launcher such as ``srun``
    or ``mpirun`` is refused with :class:`ValueError` when a prefix applies.

    :param argv: The ABINIT command argument vector, without the input file.
    :param directory: Run ABINIT in this directory.
    :param input_file: The input file name in *directory*.
    :param log_file: Save standard output under this name in *directory*.
    :param timeout: Stop the process after this many seconds when set.
    :param launch: Prepend the attempt's launch prefix when true, the default (``None``);
        ``False`` runs *argv* as given.
    :param termination_grace: Allow this many seconds for graceful termination.
    :param report_path: Write the report at this directory-relative path.
    :return: The classified run report.
    """

    root = Path(directory).resolve()
    output_file = Path(input_file).stem + ".abo"
    output = root / output_file
    output.unlink(missing_ok=True)
    log = root / log_file
    # ponytail: no live monitor or remedy ladder; add them when a real campaign needs them.
    process = ProcessSupervisor().run(
        [*launch_command(argv, launch=launch is not False), input_file],
        timeout=timeout,
        cwd=root,
        termination_grace=termination_grace,
        stdout_path=log,
        stderr_path=log.with_suffix(".err"),
    )
    diagnostics = (*process.diagnostics, *diagnose_abinit(root, output=output_file))
    codes = {item.code for item in diagnostics}
    if process.timed_out:
        classification = "timeout"
    elif "abinit.error" in codes:
        classification = "crashed"
    elif process.returncode or "abinit.incomplete" in codes:
        classification = "process_failure"
    elif "abinit.scf_not_converged" in codes:
        classification = "nonconverged"
    elif any(item.severity in {"error", "fatal"} for item in diagnostics):
        classification = "process_failure"
    else:
        classification = "completed"
    report = AbinitRunReport(process, classification, diagnostics, _parse(_read(output)))
    report.write(root / report_path)
    return report
