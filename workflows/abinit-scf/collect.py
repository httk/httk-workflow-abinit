"""Collect hook for the ``abinit.scf`` workflow.

The run leaves ``run.abo`` in the persistent workdir.
"""

from httk.codes.abinit.collect import read_total_energy


def collect(record):
    """Return the converged total energy of the run.

    :param record: The collected job record.
    :return: The ``total_energy`` output role.
    """
    return {"total_energy": read_total_energy(record.result_file("run.abo"))}
