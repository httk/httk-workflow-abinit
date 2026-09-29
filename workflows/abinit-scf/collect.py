"""Collect hook for the ``abinit.scf`` workflow."""

from httk.codes.abinit import collect_abinit


def collect(record):
    """Extract the converged total energy from the job record.

    :param record: The collected job record.
    :return: The ``total_energy`` output role.
    """
    return collect_abinit(record)
