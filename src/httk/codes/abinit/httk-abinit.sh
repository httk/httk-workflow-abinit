#!/usr/bin/env bash

# Native httk ABINIT Bash API, version 1. Source httk-workflow.sh first.
#
# Every function is one abinit-* bridge subcommand, and every option of that
# subcommand is available here: the arguments are passed through untouched.
#
#   httk_abinit_write_input --options OPTIONS.json [--input run.abi]
#   httk_abinit_run [--directory .] [--input run.abi] [--log abinit.log] [--timeout S] -- abinit ...
#       prints the report path; exits 0 completed, 20 crashed, 21 nonconverged,
#       22 process failure, 124 timeout
#   httk_abinit_energy [--output run.abo] [--unit ha|ev]   exits 1 when there is no energy
#   httk_abinit_converged [--output run.abo]               exits 1 when not converged
#   httk_abinit_diagnose [--output run.abo] [--json]       exits 20 when it found anything
HTTK_ABINIT_BASH_API_VERSION=1

_httk_abinit_require_workflow_api() {
    if ! declare -F _httk_workflow_bridge >/dev/null 2>&1; then
        printf 'httk-workflow: source HTTK_WORKFLOW_BASH_API before HTTK_WORKFLOW_ABINIT_BASH_API\n' >&2
        return 2
    fi
}

httk_abinit_write_input() {
    _httk_abinit_require_workflow_api || return
    _httk_workflow_bridge abinit-write-input "$@"
}

httk_abinit_run() {
    _httk_abinit_require_workflow_api || return
    _httk_workflow_bridge abinit-run "$@"
}

httk_abinit_energy() {
    _httk_abinit_require_workflow_api || return
    _httk_workflow_bridge abinit-energy "$@"
}

httk_abinit_converged() {
    _httk_abinit_require_workflow_api || return
    _httk_workflow_bridge abinit-converged "$@"
}

httk_abinit_diagnose() {
    _httk_abinit_require_workflow_api || return
    _httk_workflow_bridge abinit-diagnose "$@"
}
