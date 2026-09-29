# Test data

Captured ABINIT 10.0.3 runs (serial, no `mpirun`, `OMP_NUM_THREADS=1`) of
diamond silicon. ABINIT names its main output after the input (`si.abi` ->
`si.abo`); only the main outputs are kept, not the log or the binary
`sio_*` files.

| File | What it is |
| --- | --- |
| `si.abi`, `si.abo` | converged SCF: `At SCF step    6, etot is converged`, final `-outvars:` `etotal -7.7807515461E+00` (the log's `Etot = -7.780752E+00 Ha`), `Calculation completed.` |
| `si_noconv.abi`, `si_noconv.abo` | `nstep 1`, `toldfe 1.0d-20`: `nstep=    1 was not enough SCF cycles to converge;`, exit status 0 |
| `error/si_err.abi`, `error/si_err.abo` | `si.abi` with the unknown variable `notavariable 3`; ABINIT stops in `chkinp` with a `--- !ERROR` block (`Found token: NOTAVARIABLE ...`, `src_file: m_parser.F90`) and exit status 13 |
| `tolerances/si_<tol>.abi`, `tolerances/si_<tol>.abo` | `si.abi` converged on another SCF tolerance, one per wording of the success line: `tolvrs 1.0d-10` (`At SCF step    7       vres2   =  8.18E-11 < tolvrs=  1.00E-10 =>converged.`), `toldff 1.0d-6` (`At SCF step    3, forces are converged :`), `tolwfr 1.0d-14` (`At SCF step   11   max residual=  9.92E-15 < tolwfr=  1.00E-14 =>converged.`), `tolrff 0.02` (`At SCF step    8, forces are sufficiently converged :`) |
| `Si.psp8` | the ONCVPSP `Si_GGA_noNLCC.psp8` norm-conserving pseudopotential |

`Si.psp8` is downloaded unmodified from
<https://raw.githubusercontent.com/abinit/abinit/master/tests/Pspdir/Si_GGA_noNLCC.psp8>.
It is part of the ABINIT test suite and is licensed under the GNU General
Public License, version 3 (GPL-3.0). The `.abo` outputs are program output of
those runs.
