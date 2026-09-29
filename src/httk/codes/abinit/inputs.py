"""Write ABINIT input files from *httk* structures."""

import os
from collections.abc import Mapping, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

__all__ = ["write_abinit_input"]

# One bohr in angstrom (CODATA 2018): ABINIT lengths default to bohr.
_BOHR_IN_ANGSTROM = 0.529177210903


def write_abinit_input(
    path: str | os.PathLike[str],
    *,
    structure: object,
    pseudopotentials: Mapping[str, str],
    ecut_ha: float,
    kpoints: tuple[int, int, int],
    pseudo_dir: str = ".",
    extra: Mapping[str, object] | None = None,
) -> Path:
    """Write an ABINIT ground-state SCF input for one periodic structure.

    The input gives the cell as ``acell 3*1.0`` and ``rprim`` rows that are the
    lattice vectors in bohr, the sites as ``ntypat``/``znucl``/``typat``/``natom``
    and reduced ``xred`` coordinates, ``ecut``, an unshifted Monkhorst-Pack grid
    (``kptopt 1``, ``ngkpt``, ``nshiftk 1``, ``shiftk 0 0 0``, which contains
    Gamma), ``nstep 50`` and ``toldfe 1e-08``, and ``pp_dirpath`` and
    ``pseudos``. An ABINIT input is inherently floating point, so the cell and
    coordinates are written as floats of the structure's exact values; a POSCAR
    path (named ``POSCAR``/``CONTCAR`` or ``*.poscar``/``*.vasp``) is read with
    its numbers exactly as written, not snapped to nearby simple fractions. This
    needs *httk-atomistic* (the ``atomistic`` extra).

    :param path: Write the input file to this path.
    :param structure: The structure: a POSCAR/CIF path or anything
        ``httk.atomistic.UnitcellStructureView`` accepts.
    :param pseudopotentials: Map every species name of the structure to its pseudopotential file name.
    :param ecut_ha: The plane-wave kinetic-energy cutoff in Ha.
    :param kpoints: The unshifted Monkhorst-Pack grid.
    :param pseudo_dir: The directory ABINIT reads the pseudopotential files from (``pp_dirpath``).
    :param extra: Additional input variables, as ``{name: value}``; they override the
        generated ones. A number is written as is, a sequence of numbers space
        separated, and a string verbatim (so ``"8 eV"`` or ``'"file.nc"'`` work).
    :return: The written path.
    :raises ValueError: If the cutoff or grid is not positive, a species has no
        pseudopotential or is not one element, or an extra value cannot be written.
    """

    from httk.atomistic import atomic_number  # pyright: ignore[reportMissingImports]

    if not ecut_ha > 0:
        raise ValueError(f"ecut_ha must be positive, not {ecut_ha!r}")
    if len(kpoints) != 3 or any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in kpoints):
        raise ValueError(f"kpoints must be three positive integers, not {kpoints!r}")
    view = _structure_view(structure)
    species = view.species
    missing = [item.name for item in species if item.name not in pseudopotentials]
    if missing:
        raise ValueError(f"no pseudopotential given for species {', '.join(missing)}")
    znucl: list[int] = []
    for item in species:
        if len(item.chemical_symbols) != 1:
            raise ValueError(f"species {item.name} is not one element: {item.chemical_symbols!r}")
        znucl.append(atomic_number(item.chemical_symbols[0]))
    index = {item.name: n for n, item in enumerate(species, start=1)}
    names = list(view.species_at_sites)
    variables: dict[str, object] = {
        "acell": "3*1.0",
        "rprim": [[float(x) / _BOHR_IN_ANGSTROM for x in row] for row in view.lattice_vectors],
        "ntypat": len(species),
        "znucl": znucl,
        "natom": len(names),
        "typat": [index[name] for name in names],
        "xred": [[float(x) for x in row] for row in view.fractional_site_positions],
        "ecut": float(ecut_ha),
        "kptopt": 1,
        "ngkpt": list(kpoints),
        "nshiftk": 1,
        "shiftk": [0.0, 0.0, 0.0],
        "nstep": 50,
        "toldfe": 1e-08,
        "pp_dirpath": _quoted(pseudo_dir),
        "pseudos": _quoted(", ".join(pseudopotentials[item.name] for item in species)),
    }
    variables.update(extra or {})
    lines: list[str] = []
    for name, value in variables.items():
        text = _value(value)
        lines.append(name + (text if text.startswith("\n") else " " + text))
    destination = Path(path)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


def _structure_view(structure: object) -> Any:
    from httk.atomistic import UnitcellStructureView, VASPStructure  # pyright: ignore[reportMissingImports]

    if not isinstance(structure, str | os.PathLike):
        return UnitcellStructureView(cast(Any, structure))
    path = Path(structure)
    # ponytail: the POSCAR names the io registry declares; a compressed POSCAR takes the generic path.
    if path.name.upper() not in {"POSCAR", "CONTCAR"} and path.suffix.lower() not in {".poscar", ".vasp"}:
        return UnitcellStructureView(path)
    from httk.atomistic.integrations.vasp.io import read_poscar  # pyright: ignore[reportMissingImports]

    # httk reads a decimal token as the simplest rational its digits allow (-1.92 as -23/12);
    # an ABINIT input wants the numbers as written, so the tokens become their exact decimal
    # values. The precision only states the coordinates' Cartesian uncertainty (no symmetry
    # is used here) and silences the reader's recommendation to give one.
    payload = dict(read_poscar(path, precision=5e-4))
    for key in ("cell", "coords"):
        payload[key] = [[Fraction(token) for token in row] for row in payload[key]]
    for key in ("scale", "volume"):
        if payload[key] is not None:
            payload[key] = Fraction(payload[key])
    return UnitcellStructureView(VASPStructure(payload))


def _quoted(text: str) -> str:
    if '"' in text:
        raise ValueError(f"cannot write {text!r} as an ABINIT string")
    return f'"{text}"'


def _value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, int | float) and not isinstance(value, bool):
        return repr(value)
    if isinstance(value, Sequence) and value and all(isinstance(row, Sequence) for row in value):
        # A matrix: one row per line, as ABINIT's own examples write rprim and xred.
        return "\n  " + "\n  ".join(_value(row) for row in cast(Sequence[object], value))
    if isinstance(value, Sequence) and value:
        return " ".join(_value(item) for item in cast(Sequence[object], value))
    raise ValueError(f"cannot write {value!r} as an ABINIT input value")
