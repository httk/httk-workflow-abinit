# Using the ABINIT helpers

*httk-workflow-abinit* ships the ABINIT helpers that workflow runners are built
on, in two languages: the Python package {py:mod}`httk.codes.abinit` and the
Bash ABINIT API, whose `httk_abinit_*` functions call the same code through the
*httk-workflow* shell bridge.

## Install

```console
python -m pip install "httk-workflow-abinit[atomistic]"
```

The distribution depends on *httk-core* and *httk-workflow*. Installing it
registers the `abinit` code through the `httk.registry.codes.abinit`
registration package, which makes the `abinit-*` bridge commands and the Bash
API available to every job the manager starts; nothing needs to be configured.
Writing inputs from structures needs *httk-atomistic*, the `atomistic` extra;
parsing, diagnostics, running and collecting do not.

## Python

```python
from httk.codes.abinit import run_abinit, write_abinit_input

write_abinit_input(
    "run.abi",
    structure="POSCAR",
    pseudopotentials={"Si": "Si.psp8"},
    ecut_ha=15,
    kpoints=(4, 4, 4),
    extra={"toldfe": 1e-10},
)
report = run_abinit(["abinit"], timeout=3600)
if report.ok:
    print(report.result.total_energy_ev)
else:
    print(report.classification, [item.code for item in report.diagnostics])
```

- {py:func}`~httk.codes.abinit.write_abinit_input` writes a ground-state SCF
  input from a POSCAR/CIF path or an *httk* structure: the cell as
  `acell 3*1.0` and `rprim` rows in bohr, `ntypat`/`znucl`/`typat`/`natom` and
  reduced `xred`, `ecut` (Ha), an unshifted Monkhorst-Pack grid (`ngkpt`,
  `shiftk 0 0 0`), `nstep 50` and `toldfe 1e-08`, and `pp_dirpath` and
  `pseudos`. `extra` adds or overrides input variables.
- {py:func}`~httk.codes.abinit.parse_abinit_output` reads the main output
  (`run.abo`) and returns an {py:class}`~httk.codes.abinit.AbinitResult`: the
  final total energy (Ha, and eV through `total_energy_ev`), taken from the
  `etotal` of the final `-outvars:` echo and reported only when the last SCF
  cycle converged; SCF convergence and step count; whether
  `Calculation completed.` was reached; and the messages of `--- !ERROR` and
  `--- !BUG` blocks. When ABINIT reports no convergence verdict (e.g. `toldff`
  on a structure whose forces vanish by symmetry), the result has
  `converged=None` and no energy, and the run may still classify `completed`;
  pick an SCF tolerance appropriate to the system.
- {py:func}`~httk.codes.abinit.run_abinit` runs the command with the input file
  appended (`abinit run.abi`) under the *httk-workflow* process supervisor,
  saves standard output (ABINIT's log) as `abinit.log`, parses the main output
  ABINIT names after the input (`run.abo`), and returns an
  {py:class}`~httk.codes.abinit.AbinitRunReport` classified as `completed`,
  `crashed`, `nonconverged`, `process_failure` or `timeout`, also written to
  `abinit-run-report.json`. A stale `run.abo` is removed first, since ABINIT
  would otherwise write `run.abo0001` beside it.
- {py:func}`~httk.codes.abinit.diagnose_abinit` diagnoses a finished calculation.

## Diagnostics

| Code | Severity | Meaning |
| --- | --- | --- |
| `abinit.error` | fatal | ABINIT stopped with a `--- !ERROR` or `--- !BUG` block; the summary is its source file and message |
| `abinit.scf_not_converged` | error | the last SCF cycle reported `nstep=N was not enough SCF cycles to converge` |
| `abinit.incomplete` | error | no `Calculation completed.` and no error block, e.g. a killed process |

A converged, completed calculation has no diagnostics.

## Bash

The manager exports the path of the ABINIT API as
`HTTK_WORKFLOW_ABINIT_BASH_API` when *httk-workflow-abinit* is installed, so a
Bash runner guards it and sources it after the generic library:

```bash
source "$HTTK_WORKFLOW_BASH_API"
: "${HTTK_WORKFLOW_ABINIT_BASH_API:?install httk-workflow-abinit}"
source "$HTTK_WORKFLOW_ABINIT_BASH_API"

httk_abinit_write_input --options options.json   # the write_abinit_input keywords as JSON
httk_abinit_run --timeout 3600 -- abinit
energy=$(httk_abinit_energy --unit ev)
```

The command names only the program: the attempt's launch prefix (the parallel start, the `HTTK_WORKFLOW_LAUNCH` variable the workflow manager sets from the `manager.launch_template` setting, or the built-in Slurm prefix) is prepended to it, and `--no-launch` (`launch=False` in Python) runs the command as given. A command that already starts with a launcher such as `mpirun` or `srun` is refused when a prefix applies.

| Function | Bridge command | Exit status |
| --- | --- | --- |
| `httk_abinit_write_input --options FILE [--input run.abi]` | `abinit-write-input` | `0` |
| `httk_abinit_run [--directory] [--input] [--log] [--timeout] [--no-launch] -- CMD...` | `abinit-run` | `0` completed, `20` crashed, `21` nonconverged, `22` process failure, `124` timeout (as `vasp-run`); prints the report path |
| `httk_abinit_energy [--output run.abo] [--unit ha\|ev]` | `abinit-energy` | `0` and the energy, `1` when there is none |
| `httk_abinit_converged [--output run.abo]` | `abinit-converged` | `0` converged, `1` not converged or unknown |
| `httk_abinit_diagnose [--output run.abo] [--json]` | `abinit-diagnose` | `0` clean, `20` when it printed diagnostics |

A refused call (for example a missing output file) exits `2`.

## The example workflow

The repository's `workflows/abinit-scf` is the workflow package `abinit.scf`:
one Python runner step that stages the `structure` input and the
pseudopotentials, writes `run.abi`, runs ABINIT, and fails with the first
diagnostic code when the calculation is not clean. Install it with
`httk plugin install` of the repository, or use it directly with
`--workflow-dir`:

```console
httk workspace settings set --key abinit.command --value abinit WORKSPACE
httk job new --workflow abinit.scf --input structure=POSCAR --file Si.psp8=Si.psp8 \
    --parameter 'pseudopotentials={"Si": "Si.psp8"}'
httk workflow run
httk collect --into results.sqlite
```

Its parameters are `pseudopotentials` (species name to file name), `ecut_ha`
(Ha, default 15) and `kpoints` (default `[4, 4, 4]`); the settings
`abinit.command` (default `abinit`) and `abinit.pseudo_dir` (default: the job's
`files/`) say how to run ABINIT and where the pseudopotential files are.

## Collecting

{py:func}`~httk.codes.abinit.collect.read_total_energy` reads the converged total
energy of a `run.abo` as a {py:class}`httk.core.DataRecord` of the property
`https://schemas.httk.org/defs/v0.1/properties/core/total_energy` in eV.

The `abinit.scf` hook shows how a workflow's `collect.py` locates the file with
`record.result_file` and returns the role mapping:

```python
from httk.codes.abinit.collect import read_total_energy


def collect(record):
    return {"total_energy": read_total_energy(record.result_file("run.abo"))}
```

### Recognized calculations

The `abinit.calculation` collector lets `httk.workflow.collect_tree(root)` (and
`httk collect DIR --into db.sqlite`) collect finished, free-standing ABINIT
runs without a workspace. A directory is recognized when it holds exactly one
`*.abo` output whose first 100 lines carry
the `.Version ... of ABINIT` banner, found by
{py:func}`~httk.codes.abinit.collect.find_outputs`, and the input `<stem>.abi`
beside it (compressed or not). A `slurm-*.out` log is ignored. Several ABINIT
outputs in one directory, or a missing input, are reported as unclaimed; an
unconverged run is claimed and then reported as a degraded item. The claim is
identified by the content of the input file. The collected role is
`total_energy`.
