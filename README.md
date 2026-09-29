# httk-workflow-abinit

![Status: Early beta](https://img.shields.io/badge/status-early--beta-orange)

> **⚠️ EARLY BETA**
>
> This is an early beta release of *httk₂*. The organization of the packages
> and their APIs should not yet be regarded as stable, and may change between
> releases.

*httk-workflow-abinit* adds ABINIT support to
[*httk-workflow*](https://github.com/httk/httk-workflow), the workflow engine of
[*httk₂*](https://github.com/httk/httk2). It provides `httk.codes.abinit`:
writing ABINIT inputs, parsing its main `.abo` output, stable diagnostics,
supervised execution with a classified run report, and a collector for workflow
outputs; and the Bash API that exposes the same helpers to Bash runners.
Installing it registers the `abinit` code with *httk₂*; nothing needs to be
configured.

## Install

```console
python -m pip install "httk-workflow-abinit[atomistic]"
```

The `atomistic` extra (*httk-atomistic*) is needed only to write inputs from
structures.

## Use

In a Python runner:

```python
from httk.codes.abinit import run_abinit, write_abinit_input

write_abinit_input("run.abi", structure="POSCAR", pseudopotentials={"Si": "Si.psp8"}, ecut_ha=15, kpoints=(4, 4, 4))
report = run_abinit(["abinit"])
print(report.classification, report.result.total_energy_ev)
```

In a Bash runner, whose manager exports the path of the ABINIT API:

```bash
source "$HTTK_WORKFLOW_BASH_API"
: "${HTTK_WORKFLOW_ABINIT_BASH_API:?install httk-workflow-abinit}"
source "$HTTK_WORKFLOW_ABINIT_BASH_API"
httk_abinit_run -- abinit
energy=$(httk_abinit_energy --unit ev)
```

A complete example workflow package, `abinit.scf`, is in
[`workflows/abinit-scf`](workflows/abinit-scf); `httk plugin install` of this
repository installs it. The API is documented in [`docs/usage.md`](docs/usage.md)
and at [docs.httk.org/httk-workflow-abinit](https://docs.httk.org/httk-workflow-abinit/).

## Running tests

`make test` runs the normal profile; `make ci` runs formatting, lint, both type
checkers and the extended tests. The end-to-end test runs the real `abinit` only
when `HTTK_TEST_ABINIT_COMMAND` names it or `abinit` is on `PATH`, and skips
otherwise.
