"""Version handling following LSST coding conventions. x

This package is used to calculate a version dynamically from a Git repository
when it is being built by ``pip``. It is not needed for EUPS-only packages,
and the calculated package version will be ``pip``-compatible and thus differ
from that produced by EUPS's ``pkgautoversion``.

It avoids the need to hard-code and continually update a version string.
It assumes the use of LSST DM release and tagging practices.
"""

from .__version__ import *
from ._versions import *
