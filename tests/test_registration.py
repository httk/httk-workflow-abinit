"""The ``abinit`` code is registered through the ``codes`` registry tier, with its citation."""

import argparse
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import httk.core  # noqa: F401  (importing httk.core runs registry discovery)
from httk.core.register import code_support, known_codes


def test_abinit_is_a_known_code_with_its_packaged_bash_api() -> None:
    assert "abinit" in known_codes()
    assert code_support("abinit").bash_api_path() == Path(str(files("httk.codes.abinit").joinpath("httk-abinit.sh")))


def test_the_bridge_mounts_the_abinit_commands() -> None:
    parser = argparse.ArgumentParser()
    code_support("abinit").resolve_bridge().add_commands(parser.add_subparsers(dest="command"))
    assert parser.parse_args(["abinit-energy"]).command == "abinit-energy"


def test_the_abinit_credit_is_registered_on_import() -> None:
    script = """
from httk.core import credits
assert "Calculations with ABINIT" not in credits.entries()
import httk.codes.abinit
assert len(credits.entries()["Calculations with ABINIT"]) == 1
"""
    subprocess.run([sys.executable, "-c", script], check=True)
