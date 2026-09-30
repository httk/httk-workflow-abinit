"""ABINIT support for *httk₂* workflows: the *httk-workflow-abinit* package.

``inputs`` writes ABINIT inputs, ``outputs`` parses its main ``.abo`` output,
``diagnostics`` classifies a finished calculation, ``reports`` runs it under
supervision, and ``collect`` reads workflow outputs out of result files, for
workflow collect hooks. This package is a thin facade re-exporting their
surface. The example workflow package ``workflows/abinit-scf`` in this
distribution's repository builds on it.
"""

from httk.core import register_citation

register_citation(
    applies_to="Calculations with ABINIT",
    references=(
        {
            "authors": ({"name": "Xavier Gonze"},),
            "note": "Gonze et al.; the DOI record lists every author",
            "title": "The ABINIT project: Impact, environment and recent developments",
            "journal": "Computer Physics Communications",
            "volume": "248",
            "pages": "107042",
            "year": "2020",
            "doi": "10.1016/j.cpc.2019.107042",
            "bib_type": "article",
        },
    ),
)

from .diagnostics import diagnose_abinit
from .inputs import write_abinit_input
from .outputs import HA_TO_EV, AbinitResult, parse_abinit_output
from .reports import AbinitRunReport, run_abinit

__all__ = [
    "HA_TO_EV",
    "AbinitResult",
    "AbinitRunReport",
    "diagnose_abinit",
    "parse_abinit_output",
    "run_abinit",
    "write_abinit_input",
]
