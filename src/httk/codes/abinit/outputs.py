"""Parse the main text output (``.abo``) of ABINIT.

Pure stdlib parsing: nothing here runs a program or imports *httk* code, so a
result can be read anywhere the output file is.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = ["HA_TO_EV", "AbinitResult", "parse_abinit_output"]

#: One hartree in electronvolts (CODATA 2018), the unit ABINIT prints energies in.
HA_TO_EV: float = 27.211386245988

# The final ``-outvars:`` echo, printed after the computation, carries ``etotal``
# (``etotalN`` per dataset) at eleven significant digits, the most any summary gives.
_OUTVARS_AFTER = "-outvars: echo values of variables after computation"
_ETOTAL = re.compile(r"^\s+etotal\d*\s+(\S+)", re.MULTILINE)
# Each SCF tolerance words its success line differently: "At SCF step 6, etot is converged :"
# (toldfe), "... vres2 = 8.18E-11 < tolvrs= 1.00E-10 =>converged." (tolvrs), "... max residual= ...
# < tolwfr= ... =>converged." (tolwfr), "At SCF step 3, forces are [sufficiently] converged :"
# (toldff, tolrff); all start "At SCF step N" and say "converged".
_CONVERGENCE = re.compile(
    r"^\s*At SCF step\s+(\d+)\b.*(?<!not )converged|nstep=\s*(\d+) was not enough SCF cycles to converge",
    re.MULTILINE,
)
# ``--- !ERROR``/``--- !BUG`` YAML documents end with ``...``; the message is the ``message: |`` block.
_ERROR_BLOCK = re.compile(r"^--- !(?:ERROR|BUG)\s*$\n(.*?)^\.\.\.\s*$", re.MULTILINE | re.DOTALL)
_MESSAGE = re.compile(r"^message: \|\s*$\n((?:^[ \t]+.*\n?)+)", re.MULTILINE)
_SOURCE = re.compile(r"^src_file:\s*(\S+)", re.MULTILINE)


@dataclass(frozen=True)
class AbinitResult:
    """What one ABINIT ``.abo`` output says about its calculation.

    :param total_energy_ha: The final total energy (``etotal`` of the final
        ``-outvars:`` echo) in Ha when the last SCF cycle converged, else ``None``.
    :param converged: Whether the last SCF cycle converged, or ``None`` when no cycle reported.
    :param scf_steps: The step count of the last SCF cycle, or ``None``.
    :param completed: Whether ABINIT reached its normal ``Calculation completed.`` end.
    :param errors: The messages of the ``--- !ERROR`` and ``--- !BUG`` blocks, each prefixed by its source file.
    """

    total_energy_ha: float | None
    converged: bool | None
    scf_steps: int | None
    completed: bool
    errors: tuple[str, ...]

    @property
    def total_energy_ev(self) -> float | None:
        """The final converged total energy in eV, or ``None``."""
        return None if self.total_energy_ha is None else self.total_energy_ha * HA_TO_EV


def parse_abinit_output(path: str | os.PathLike[str]) -> AbinitResult:
    """Parse one ABINIT main output file (``<input stem>.abo``).

    When ABINIT reports no convergence verdict (e.g. ``toldff`` on a structure
    whose forces vanish by symmetry), the result has ``converged=None`` and no
    energy, and a supervised run may still classify ``completed``; pick an SCF
    tolerance appropriate to the system.

    :param path: Read the ABINIT main output at this path.
    :return: The parsed result.
    :raises FileNotFoundError: If the output file does not exist.
    """

    return _parse(Path(path).read_text(encoding="utf-8", errors="replace"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _parse(text: str) -> AbinitResult:
    cycles = _CONVERGENCE.findall(text)
    converged = None if not cycles else bool(cycles[-1][0])
    _, marker, final = text.rpartition(_OUTVARS_AFTER)
    # ponytail: the last etotal of the final echo is the last dataset's; a multi-dataset
    # result (one energy per dataset) needs a per-dataset list when a workflow runs one.
    energies = _ETOTAL.findall(final) if marker else []
    errors: list[str] = []
    for block in _ERROR_BLOCK.findall(text):
        message = _MESSAGE.search(block)
        body = " ".join(line.strip() for line in message.group(1).splitlines() if line.strip()) if message else ""
        source = _SOURCE.search(block)
        entry = f"{source.group(1)}: {body}" if source else body
        if entry and entry not in errors:
            errors.append(entry)
    return AbinitResult(
        total_energy_ha=float(energies[-1]) if energies and converged else None,
        converged=converged,
        scf_steps=int(cycles[-1][0] or cycles[-1][1]) if cycles else None,
        completed="Calculation completed." in text,
        errors=tuple(errors),
    )
