"""Register the ABINIT code support implemented by :mod:`httk.codes.abinit`."""

from httk.core.register import register_code

register_code("abinit", bridge="httk.codes.abinit._bridge", bash_api="httk.codes.abinit:httk-abinit.sh")
