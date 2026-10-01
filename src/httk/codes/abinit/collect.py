"""Building blocks for the collect hooks of ABINIT workflows."""

from pathlib import Path

from httk.core import DataRecord
from httk.core.datastream.compression import open_compressed, split_compression_suffix

from .outputs import parse_abinit_output

__all__ = ["find_outputs", "read_total_energy"]

_TOTAL_ENERGY_DEFINITION = "https://schemas.httk.org/defs/v0.1/properties/core/total_energy"
_TOTAL_ENERGY_NAME = "_httk_total_energy"
_EXTENSIONS = (".abo",)
_BANNER = b"of ABINIT, released"
_HEAD_LINES = 100


def _has_banner(path: Path) -> bool:
    try:
        with path.open("rb") as raw, open_compressed(raw, compression="extension", name=path.name) as stream:
            for _, line in zip(range(_HEAD_LINES), stream, strict=False):
                if _BANNER in line:
                    return True
    except (OSError, EOFError, ValueError):
        pass
    return False


def find_outputs(directory: Path) -> tuple[Path, ...]:
    """Find the ABINIT output files of a directory by their start-of-file banner.

    Only the first 100 lines of each candidate are read, so unrelated files
    such as scheduler logs are rejected cheaply. Compressed files are found too.

    :param directory: The directory to search.
    :return: The output files, sorted by name.
    """

    found = []
    for path in sorted(Path(directory).iterdir()):
        stem, _ = split_compression_suffix(path.name)
        if stem.lower().endswith(_EXTENSIONS) and path.is_file() and _has_banner(path):
            found.append(path)
    return tuple(found)


def read_total_energy(path: Path) -> DataRecord:
    """Read the converged total energy, in eV, of one ABINIT output file.

    :param path: The ABINIT output file.
    :return: The ``total_energy`` property as a data record.
    :raises ValueError: If the file is incomplete or holds no converged total energy.
    """

    result = parse_abinit_output(path)
    energy = result.total_energy_ev
    if energy is None:
        raise ValueError(f"{path} holds no converged total energy")
    if not result.completed:
        raise ValueError(f"{path} is incomplete: ABINIT did not report Calculation completed.")
    return DataRecord.from_value(_TOTAL_ENERGY_DEFINITION, _TOTAL_ENERGY_NAME, energy)
