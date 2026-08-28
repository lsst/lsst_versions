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

"""In-tree PEP 517 build backend used to build this package itself.

The ``setuptools.finalize_distribution_options`` entry point provided by this
package can only be used by packages that have ``lsst_versions`` installed,
so it is unavailable while this package is being built. This backend fills
that gap by writing the version file before delegating every build hook to
``setuptools.build_meta``. The version itself is then picked up from that
file by the ``tool.setuptools.dynamic.version`` setting.
"""

from __future__ import annotations

__all__ = [
    "build_editable",
    "build_sdist",
    "build_wheel",
    "get_requires_for_build_editable",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_editable",
    "prepare_metadata_for_build_wheel",
]

import os
import re
import warnings

from setuptools.build_meta import build_editable as _build_editable
from setuptools.build_meta import build_sdist as _build_sdist
from setuptools.build_meta import build_wheel as _build_wheel
from setuptools.build_meta import (
    get_requires_for_build_editable,  # noqa: F401
    get_requires_for_build_sdist,  # noqa: F401
    get_requires_for_build_wheel,  # noqa: F401
)
from setuptools.build_meta import (
    prepare_metadata_for_build_editable as _prepare_metadata_for_build_editable,
)
from setuptools.build_meta import prepare_metadata_for_build_wheel as _prepare_metadata_for_build_wheel

# The root of this package's source tree, two levels above this file.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Used when no version can be determined from Git or from a previously
# written version file.
_DEFAULT_VERSION = "0.0.1"

_ConfigSettings = dict[str, str | list[str]] | None


def _read_written_version(version_path: str) -> str | None:
    """Read the version from a previously written version file.

    Parameters
    ----------
    version_path : `str`
        Path to the version file.

    Returns
    -------
    version : `str` or `None`
        The version found in the file, or `None` if there is no such file
        or it contains no version.
    """
    if not os.path.isfile(version_path):
        return None

    with open(version_path) as fh:
        content = fh.read()

    # Use a regex to extract the version rather than executing the version
    # file. Only this package writes that file so its form is known.
    if match := re.search(r'__version__\s*=\s*"(.*)"', content):
        return match.group(1)
    return None


def _write_version_file() -> None:
    """Determine the version of this package and write the version file."""
    from ._versions import _find_version_path, _write_version, get_lsst_version

    version_path = _find_version_path(_ROOT)
    if version_path is None:
        # _find_version_path has already warned.
        return

    try:
        # Falling back to package metadata allows a source distribution that
        # is no longer part of a Git repository to be built.
        version = get_lsst_version(_ROOT, fallback=True)
    except Exception as e:
        # Git exceptions sometimes have no error message.
        msg = str(e) or repr(e)
        print(f"Failed to determine package version from Git: {msg}")

        written_version = _read_written_version(version_path)
        if written_version is None:
            warnings.warn("Unable to determine package version. Falling back to default value.", stacklevel=2)
            written_version = _DEFAULT_VERSION
        version = written_version

    _write_version(version, version_path)


def build_wheel(
    wheel_directory: str,
    config_settings: _ConfigSettings = None,
    metadata_directory: str | None = None,
) -> str:
    """Build a wheel, writing the version file first."""
    _write_version_file()
    return _build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory: str, config_settings: _ConfigSettings = None) -> str:
    """Build a source distribution, writing the version file first."""
    _write_version_file()
    return _build_sdist(sdist_directory, config_settings)


def build_editable(
    wheel_directory: str,
    config_settings: _ConfigSettings = None,
    metadata_directory: str | None = None,
) -> str:
    """Build an editable wheel, writing the version file first."""
    _write_version_file()
    return _build_editable(wheel_directory, config_settings, metadata_directory)


def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings: _ConfigSettings = None) -> str:
    """Prepare wheel metadata, writing the version file first."""
    _write_version_file()
    return _prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def prepare_metadata_for_build_editable(
    metadata_directory: str, config_settings: _ConfigSettings = None
) -> str:
    """Prepare editable wheel metadata, writing the version file first."""
    _write_version_file()
    return _prepare_metadata_for_build_editable(metadata_directory, config_settings)
