#!/usr/bin/env python

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

# Follow setuptools_scm bootstrapping approach.
# The setuptools entry point can not be used to derive this package
# version so it needs to be written here.
import os
import re
import sys
import warnings

from setuptools import setup


def _write_version(version: str, path: str) -> None:
    with open(path, "w") as fh:
        print(
            f"""__all__ = ["__version__"]
__version__ = "{version}"
""",
            file=fh,
            end="",
        )


def scm_version():
    """Determine the version of this package."""
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "python")
    sys.path.insert(0, src)

    version_path = os.path.join(here, "python", "lsst_versions", "__version__.py")

    # To allow import to work, write a stub version file.
    default_version = "0.0.1"
    if not os.path.exists(version_path):
        _write_version(default_version, version_path)

    # Finding a version may well fail if there is no git repo
    # associated with this checkout.
    try:
        from lsst_versions import find_lsst_version

        version = find_lsst_version(here, "HEAD")
    except Exception as e:
        # git exceptions sometimes have no error message.
        msg = str(e)
        if not msg:
            msg = repr(e)
        print(f"Failed to determine package version from Git: {msg}")
        version = None

    if version is None:
        # Look for an existing version file and read it.
        with open(version_path) as fh:
            content = fh.read()

        # Use regex to extract version rather than trying to execute
        # the (possibly untrusted) version code directly. This file
        # should match the form we write above (no other system should
        # be writing it).
        if match := re.search(r'__version__\s*=\s*"(.*)"', content):
            version = match.group(1)
        else:
            version = default_version

        if version == default_version:
            warnings.warn("Unable to determine package version. Falling back to default value.")

    _write_version(version, version_path)

    return version


setup(
    version=scm_version(),
)
