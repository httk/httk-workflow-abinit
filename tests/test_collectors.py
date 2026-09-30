"""Recognized-calculation collection of finished free-standing ABINIT runs."""

import bz2
import lzma
import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from httk.workflow import claims, collect_tree

from conftest import DATA
from httk.codes.abinit.collect import find_outputs
from httk.codes.abinit.outputs import parse_abinit_output

NAME = "abinit.calculation"
ENERGY = -211.7250356049954


def _run(directory: Path, *, source: str = "si", compress: bool = False) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for ext in ("abo", "abi"):
        data = (DATA / f"{source}.{ext}").read_bytes()
        if compress:
            (directory / f"si.{ext}.bz2").write_bytes(bz2.compress(data))
        else:
            (directory / f"si.{ext}").write_bytes(data)
    return directory


def test_a_converged_run_is_collected(tmp_path: Path) -> None:
    _run(tmp_path / "a")
    (job,) = list(collect_tree(tmp_path))
    assert (job.run.source_id or "").startswith(f"{NAME}:")
    (claim,) = [c for c in claims(tmp_path) if c.kind == "claimed"]
    assert job.run.source_id == f"{NAME}:{claim.identity}"
    assert cast(Any, job.outputs["total_energy"]).value == pytest.approx(ENERGY)


def test_an_unconverged_run_is_claimed_and_degraded(tmp_path: Path) -> None:
    _run(tmp_path / "a", source="si_noconv")
    assert [c.kind for c in claims(tmp_path)] == ["claimed"]
    (job,) = list(collect_tree(tmp_path))
    assert job.outputs.get("total_energy") is None


def test_a_scheduler_log_is_no_candidate(tmp_path: Path) -> None:
    (tmp_path / "slurm-1.out").write_text("starting job\n" * 5, encoding="utf-8")
    assert find_outputs(tmp_path) == ()
    assert list(claims(tmp_path)) == []
    assert list(collect_tree(tmp_path)) == []


def test_two_outputs_are_unclaimed(tmp_path: Path) -> None:
    _run(tmp_path / "a")
    shutil.copy(DATA / "si.abo", tmp_path / "a" / "other.abo")
    (only,) = claims(tmp_path)
    assert only.kind == "unclaimed"
    assert only.reason is not None and "several" in only.reason and "other.abo" in only.reason


def test_a_missing_input_is_unclaimed(tmp_path: Path) -> None:
    _run(tmp_path / "a")
    (tmp_path / "a" / "si.abi").unlink()
    (only,) = claims(tmp_path)
    assert only.kind == "unclaimed"
    assert only.reason == "no si.abi beside si.abo"


def test_compressed_files_are_collected(tmp_path: Path) -> None:
    directory = _run(tmp_path / "a", compress=True)
    packed = directory / "si.abi.bz2"
    (directory / "si.abi.lzma").write_bytes(
        lzma.compress(bz2.decompress(packed.read_bytes()), format=lzma.FORMAT_ALONE)
    )
    packed.unlink()
    (job,) = list(collect_tree(tmp_path))
    assert cast(Any, job.outputs["total_energy"]).value == pytest.approx(ENERGY)


def test_a_dotted_stem_finds_its_input(tmp_path: Path) -> None:
    _run(tmp_path / "a")
    directory = tmp_path / "a"
    (directory / "si.abo").rename(directory / "si.relax.abo")
    (directory / "si.abi").rename(directory / "si.relax.abi")
    (only,) = claims(tmp_path)
    assert only.kind == "claimed"
    (directory / "si.relax.abi").unlink()
    (only,) = claims(tmp_path)
    assert only.reason == "no si.relax.abi beside si.relax.abo"


def test_a_compressed_output_parses_like_the_plain_one(tmp_path: Path) -> None:
    packed = tmp_path / "si.abo.bz2"
    packed.write_bytes(bz2.compress((DATA / "si.abo").read_bytes()))
    assert parse_abinit_output(packed) == parse_abinit_output(DATA / "si.abo")
