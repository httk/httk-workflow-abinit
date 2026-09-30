"""Recognize a finished ABINIT run: one ABINIT output beside its input file."""

from pathlib import Path, PurePath

from httk.core.datastream.compression import split_compression_suffix
from httk.workflow.calculations import content_digest
from httk.workflow.collecting import existing_file
from httk.workflow.hookapi import Claim, Unclaimed

from httk.codes.abinit.collect import find_outputs


def recognize(directory: Path) -> Claim | Unclaimed | None:
    """Claim a directory holding exactly one ABINIT output and its input.

    :param directory: The directory to examine.
    :return: A claim identified by the input file's content, an unclaimed reason, or ``None``.
    """
    outputs = list(find_outputs(directory))
    if not outputs:
        return None
    if len(outputs) > 1:
        return Unclaimed(f"several ABINIT outputs: {', '.join(path.name for path in outputs)}")
    output = outputs[0]
    stem = PurePath(split_compression_suffix(output.name)[0]).stem
    name = f"{stem}.abi"
    if existing_file(directory / name) is None:
        return Unclaimed(f"no {name} beside {output.name}")
    return Claim(content_digest(directory, [name]))
