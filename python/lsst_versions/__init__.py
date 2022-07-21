# This file is part of lsst_versions.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# Use of this source code is governed by a 3-clause BSD-style
# license that can be found in the LICENSE file.

"""Version handling following LSST coding conventions.

This package is used to calculate a version dynamically from a Git repository
when it is being built by ``pip``. It is not needed for EUPS-only packages,
and the calculated package version will be ``pip``-compatible and thus differ
from that produced by EUPS's ``pkgautoversion``.

It avoids the need to hard-code and continually update a version string.
It assumes the use of LSST DM release and tagging practices.
"""
try:
    from .__version__ import *
except:
    pass

# Importing __all__ ensures that the docstrings for the public APis
# in _versions.py are lifted into the main namespace.
from ._versions import *
from ._versions import __all__
