"""Building blocks for the collect hooks of ABINIT workflows."""

from pathlib import Path

from httk.core import DataRecord

from .outputs import parse_abinit_output

__all__ = ["read_total_energy"]

_TOTAL_ENERGY_DEFINITION = "https://schemas.httk.org/defs/v0.1/properties/core/total_energy"
_TOTAL_ENERGY_NAME = "_httk_total_energy"


def read_total_energy(path: Path) -> DataRecord:
    """Read the converged total energy, in eV, of one ABINIT output file.

    :param path: The ABINIT output file.
    :return: The ``total_energy`` property as a data record.
    :raises ValueError: If the file holds no converged total energy.
    """

    energy = parse_abinit_output(path).total_energy_ev
    if energy is None:
        raise ValueError(f"{path} holds no converged total energy")
    return DataRecord.from_value(_TOTAL_ENERGY_DEFINITION, _TOTAL_ENERGY_NAME, energy)
