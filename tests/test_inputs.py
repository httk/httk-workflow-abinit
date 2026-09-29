"""``write_abinit_input`` writes an input the real ``abinit`` accepts."""

import logging
import os
import subprocess
from pathlib import Path

import pytest

from conftest import DATA, SILICON_POSCAR, abinit_command, requires_abinit
from httk.codes.abinit import parse_abinit_output, write_abinit_input

pytest.importorskip("httk.atomistic")

_ROCKSALT_POSCAR = """NaCl
5.64
0.0 0.5 0.5
0.5 0.0 0.5
0.5 0.5 0.0
Na Cl
1 1
Direct
0.0 0.0 0.0
0.5 0.5 0.5
"""


def _write(tmp_path: Path, poscar: str = SILICON_POSCAR, **extra: object) -> str:
    (tmp_path / "POSCAR").write_text(poscar, encoding="utf-8")
    options: dict[str, object] = {
        "structure": tmp_path / "POSCAR",
        "pseudopotentials": {"Si": "Si.psp8"},
        "ecut_ha": 8.0,
        "kpoints": (2, 2, 2),
    }
    write_abinit_input(tmp_path / "run.abi", **(options | extra))  # type: ignore[arg-type]
    return (tmp_path / "run.abi").read_text(encoding="utf-8")


def test_the_input_has_the_cell_sites_and_settings(tmp_path: Path) -> None:
    text = _write(tmp_path, extra={"toldfe": 1e-10, "ecut": "300 eV", "nband": 8})
    lines = text.splitlines()
    for line in ("acell 3*1.0", "ntypat 1", "znucl 14", "natom 2", "typat 1 1", "ecut 300 eV", "nband 8"):
        assert line in lines
    for line in ("kptopt 1", "ngkpt 2 2 2", "nshiftk 1", "shiftk 0.0 0.0 0.0", "nstep 50", "toldfe 1e-10"):
        assert line in lines
    assert 'pp_dirpath "."' in lines and 'pseudos "Si.psp8"' in lines
    rprim = lines[lines.index("rprim") + 1 : lines.index("rprim") + 4]
    # 5.4293 angstrom / 2 in bohr: the 10.26 bohr cubic cell of the captured si.abi.
    assert [float(x) for row in rprim for x in row.split()] == pytest.approx(
        [0, 5.13, 5.13, 5.13, 0, 5.13, 5.13, 5.13, 0], abs=1e-4
    )
    assert lines[lines.index("xred") + 1 : lines.index("xred") + 3] == ["  0.0 0.0 0.0", "  0.25 0.25 0.25"]


def test_species_map_to_atomic_numbers_and_pseudopotentials_in_order(tmp_path: Path) -> None:
    text = _write(tmp_path, _ROCKSALT_POSCAR, pseudopotentials={"Cl": "Cl.psp8", "Na": "Na.psp8"})
    lines = text.splitlines()
    assert {"ntypat 2", "znucl 11 17", "typat 1 2", 'pseudos "Na.psp8, Cl.psp8"'} <= set(lines)


def test_invalid_options_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no pseudopotential given for species Si"):
        _write(tmp_path, pseudopotentials={"Ge": "Ge.psp8"})
    with pytest.raises(ValueError, match="kpoints"):
        _write(tmp_path, kpoints=(2, 0, 2))
    with pytest.raises(ValueError, match="ecut_ha"):
        _write(tmp_path, ecut_ha=0)
    with pytest.raises(ValueError, match="cannot write"):
        _write(tmp_path, extra={"nband": None})


@requires_abinit
def test_the_real_abinit_accepts_the_input(tmp_path: Path) -> None:
    command = abinit_command()
    assert command is not None
    _write(tmp_path)
    (tmp_path / "Si.psp8").symlink_to(DATA / "Si.psp8")
    with (tmp_path / "abinit.log").open("wb") as log:
        subprocess.run(
            [*command, "run.abi"],
            cwd=tmp_path,
            stdout=log,
            stderr=subprocess.DEVNULL,
            env=os.environ | {"OMP_NUM_THREADS": "1"},
            check=True,
            timeout=300,
        )
    result = parse_abinit_output(tmp_path / "run.abo")
    assert result.converged and result.completed
    assert result.total_energy_ha == pytest.approx(-7.78075, abs=1e-4)


_HEXAGONAL_POSCAR = """hexagonal zinc, few-digit values httk would otherwise snap (-1.92 to -23/12)
1.0
3.3256 -1.92 0.0
0.0 3.84 0.0
0.0 0.0 6.35
Zn
2
Direct
0.333333 0.666667 0.25
0.666667 0.333333 0.75
"""


def test_a_poscar_is_written_with_its_numbers_as_given_and_no_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        text = _write(tmp_path, _HEXAGONAL_POSCAR, pseudopotentials={"Zn": "Zn.psp8"})
    assert [record for record in caplog.records if record.levelno >= logging.WARNING] == []
    lines = text.splitlines()
    rprim = [[float(x) for x in row.split()] for row in lines[lines.index("rprim") + 1 : lines.index("rprim") + 4]]
    bohr = 0.529177210903
    assert rprim == [[3.3256 / bohr, -1.92 / bohr, 0.0], [0.0, 3.84 / bohr, 0.0], [0.0, 0.0, 6.35 / bohr]]
    xred = lines[lines.index("xred") + 1 : lines.index("xred") + 3]
    assert xred == ["  0.333333 0.666667 0.25", "  0.666667 0.333333 0.75"]
