"""Shared test configuration: isolate the httk configuration of every test."""

import os
import shlex
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

# Keep each BLAS runtime of the many short-lived runner processes to one thread;
# child runners inherit this.
for _thread_limit in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_thread_limit] = "1"


@pytest.fixture(autouse=True)
def _isolated_httk_config(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every test its own httk config and data home, so no workspace registry leaks between tests."""

    monkeypatch.setenv("HTTK_CONFIG_HOME", str(tmp_path_factory.mktemp("httk-config")))
    monkeypatch.setenv("HTTK_DATA_HOME", str(tmp_path_factory.mktemp("httk-store")))


DATA = Path(__file__).resolve().parent / "data"
REPO_ROOT = Path(__file__).resolve().parent.parent

# Diamond silicon, the structure of the captured tests/data/si.abi (acell 3*10.26 bohr).
SILICON_POSCAR = """silicon
5.4293
0.0 0.5 0.5
0.5 0.0 0.5
0.5 0.5 0.0
Si
2
Direct
0.00 0.00 0.00
0.25 0.25 0.25
"""


def abinit_command() -> list[str] | None:
    """The real ``abinit`` command: ``HTTK_TEST_ABINIT_COMMAND``, else ``abinit`` on PATH, else ``None``."""

    command = os.environ.get("HTTK_TEST_ABINIT_COMMAND") or shutil.which("abinit")
    return shlex.split(command) if command else None


requires_abinit = pytest.mark.skipif(
    abinit_command() is None, reason="needs a real abinit: set HTTK_TEST_ABINIT_COMMAND or put abinit on PATH"
)


@pytest.fixture
def installed_plugin(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Install this repository's workflows as the plugin ``httk plugin install`` would, into the isolated data home."""

    from httk.core.plugins import install_plugin
    from httk.workflow.packages import _reset_plugin_workflow_cache

    source = tmp_path_factory.mktemp("plugin-source") / "httk-workflow-abinit"
    shutil.copytree(REPO_ROOT / "workflows", source / "workflows", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(REPO_ROOT / "httk_plugin.toml", source)
    install_plugin(source)
    _reset_plugin_workflow_cache()
    yield
    _reset_plugin_workflow_cache()
