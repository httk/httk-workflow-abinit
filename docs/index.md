# *httk-workflow-abinit*

This site documents the *httk-workflow-abinit* module. For the full
documentation of *httk₂*, see [docs.httk.org](https://docs.httk.org).

The module adds ABINIT support to *httk-workflow*: the Python helpers in
`httk.codes.abinit` (input writing, output parsing, diagnostics, supervised
execution and result-reading helpers), the Bash API a Bash runner sources as
`$HTTK_WORKFLOW_ABINIT_BASH_API`, and the `abinit-*` bridge commands behind that
API. Installing it registers the `abinit` code with *httk₂* through the
`httk.registry.codes.abinit` registration package. The repository also carries
the example workflow package `abinit.scf`.

```{admonition} Quick links
:class: tip

- {doc}`usage` — the Python and Bash API, the example workflow, and the diagnostics
- {doc}`reference/index` — the generated API reference
```

## Install

```console
python -m pip install "httk-workflow-abinit[atomistic]"
```

```{toctree}
:maxdepth: 2
:caption: Documentation

usage
reference/index
```
