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
that gap by writing the ``VERSION`` file before delegating every build hook
to ``setuptools.build_meta``. The version itself is then picked up from that
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
import warnings
from pathlib import Path

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
_ROOT = Path(__file__).absolute().parent.parent.parent

# Used when no version can be determined from Git or from a previously
# written version file.
_DEFAULT_VERSION = "0.0.1"

_ConfigSettings = dict[str, str | list[str]] | None


def _version_path(root: str | os.PathLike[str]) -> Path:
    """Return the path to the plain text version file.

    Parameters
    ----------
    root : `str` or `os.PathLike`
        Root of the source tree.

    Returns
    -------
    path : `pathlib.Path`
        Path to the ``VERSION`` file that is read by the
        ``tool.setuptools.dynamic.version`` setting.
    """
    return Path(root) / "VERSION"


def _read_written_version(root: str | os.PathLike[str] = _ROOT) -> str | None:
    """Read the version from a previously written ``VERSION`` file.

    Parameters
    ----------
    root : `str` or `os.PathLike`, optional
        Root of the source tree.

    Returns
    -------
    version : `str` or `None`
        The version found in the file, or `None` if there is no such file
        or it is empty.
    """
    path = _version_path(root)
    if not path.is_file():
        return None

    return path.read_text().strip() or None


def _write_version_file(root: str | os.PathLike[str] = _ROOT) -> None:
    """Determine the version of a source tree and write the ``VERSION`` file.

    Parameters
    ----------
    root : `str` or `os.PathLike`, optional
        Root of the source tree.
    """
    from ._versions import get_lsst_version

    try:
        # Falling back to package metadata allows a source distribution that
        # is no longer part of a Git repository to be built.
        version = get_lsst_version(root, fallback=True)
    except Exception as e:
        # Git exceptions sometimes have no error message.
        msg = str(e) or repr(e)
        print(f"Failed to determine package version from Git: {msg}")

        written_version = _read_written_version(root)
        if written_version is None:
            warnings.warn("Unable to determine package version. Falling back to default value.", stacklevel=2)
            written_version = _DEFAULT_VERSION
        version = written_version

    _version_path(root).write_text(version + "\n")


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
