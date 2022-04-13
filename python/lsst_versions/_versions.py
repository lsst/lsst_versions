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

"""Functions to support version discovery using LSST conventions."""

from __future__ import annotations

__all__ = ["find_dev_lsst_version", "infer_version_for_setuptools"]

import logging
import os
import warnings
from typing import TYPE_CHECKING, Dict

try:
    import tomli
except ImportError:
    tomli = None  # type: ignore

try:
    import git
except ImportError:
    git = None  # type: ignore

if TYPE_CHECKING:
    import setuptools


log = logging.getLogger(__name__)


def find_dev_lsst_version(repo_dir: str, version_commit: str) -> str:
    """Return the development version for the given LSST commit.

    Parameters
    ----------
    repo_dir : `str`
        Path to the relevant Git repository.
    version_commit : `str`
        Commit for which the version is to be calculated.

    Returns
    -------
    dev_version : `str`
        The development version of the commit.

    Notes
    -----
    This function is specifically designed to determine versions for LSST
    Science Pipelines packages that follow the conventions in the
    `Developer Guide <https://developer.lsst.io>`_.
    Specifically:

    * Weekly tags are applied to ``main`` of the form ``w.YYYY.WW`` where
      ``YYYY`` is the year and ``WW`` is the week in the year.
    * Releases are created with tags that use the form ``vNN.x.y*``.
    * Release tags on ``main`` are always associated with a weekly but then
      branch. If an rc is made on one weekly and then a new rc is made on
      another weekly, there may be inconsistent naming.
    * The general development process involves rebasing rather than merging
      without rebasing.

    A development version is derived by:

    #. Determine the highest branch/tag ``vNN`` that does not have this
       commit as an ancestor.
    #. The closest ``w.YYYY.WW`` tag.
    #. The number of commits from this commit to the closest weekly tag, ``c``.
    #. Creating a new version of ``(NN+1).0.0aYYYYWWCC``

    """
    if git is None:
        raise RuntimeError("GitPython package not installed. Unable to determine version.")

    repo = git.Repo(repo_dir)

    releases: Dict[int, git.objects.commit.Commit] = {}
    weeklies: Dict[str, str] = {}
    for tagref in repo.tags:
        tag_name = str(tagref)
        # v tags for release candidates only appear for v13 onwards.
        # Ignore older releases.
        if tag_name.startswith("v"):
            release = tagref.tag
            if release is None:
                continue
            # Assume that only major releases matter when looking through
            # the history.
            major = tag_name[1:].split(".")[0]
            if major:
                releases[int(major)] = release.object
        elif tag_name.startswith("w."):
            weekly = tagref.tag
            if weekly is None:
                continue

            # There can be multiple weeklies associated with a single
            # commit. Retain the newest weekly. Some weekly tags did not
            # zero pad the week so must be normalized before comparison.
            if len(tag_name) == 8:
                tag_name = f"{tag_name[:7]}0{tag_name[-1]}"

            # Store the weeklies associated with the object they are tagging
            # but only if this weekly is more recent than the one that may
            # already be stored.
            hexsha = weekly.object.hexsha
            if (previous := weeklies.get(hexsha, None)) and previous > tag_name:
                continue
            weeklies[hexsha] = tag_name

    commit = repo.commit(version_commit)

    # Scan through all the releases for the first that does not have this
    # commit as an ancestor.
    relevant_release = 0
    for major_release in sorted(releases, reverse=True):
        if not repo.is_ancestor(commit, releases[major_release]):
            relevant_release = major_release
            break
        if commit == releases[major_release]:
            # It may be the actual release that should not be a dev
            # release at all, but for now we do not try to look for
            # release (non-rc) tags to deal with this properly.
            relevant_release = major_release - 1
            break

    if relevant_release == 0:
        warnings.warn(f"Could not find release tag in repo '{repo_dir}', using 0.")

    # Look through the parents until we find a weekly commit.
    # The counter can report confusing results if this is being used for
    # an unmerged development branch (and on GitHub a pull request will
    # include an extra commit because it merges the branch for testing).
    counter = 0
    weekly_name = ""
    while commit:
        if (hexsha := commit.hexsha) in weeklies:
            weekly_name = weeklies[hexsha]
            break
        parents = commit.parents
        if parents:
            commit = parents[0]
        else:
            break
        counter += 1

    if not weekly_name:
        # No weekly was found. This must be a very early commit.
        year, week = "0", "0"
    else:
        year, week = weekly_name[2:].split(".")

    # Python pre-release versions must can only have a single integer
    # after the "a".
    dev_version = f"{relevant_release + 1}.0.0a{int(year):04d}{int(week):02d}{counter:02d}"
    log.debug(
        "Using version %s for commit %s derived from weekly %s", dev_version, commit.hexsha, weekly_name
    )

    return dev_version


def _write_version(version: str, version_path: str) -> None:
    """Write the version information to the specified file."""
    with open(version_path, "w") as fh:
        print(
            f"""__all__ = ["__version__"]
__version__ = "{version}"
""",
            file=fh,
            end="",
        )


def infer_version_for_setuptools(dist: setuptools.Distribution) -> None:
    """Infer the version and write to the configuration location.

    This function should have been registered as a
    ``setuptools.finalize_distribution_options`` entry point.

    Parameters
    ----------
    dist : `setuptools.Distribution`
        The setuptools distribution object triggering this code. It will
        be updated to store the calculated version.

    Notes
    -----
    Will look for an entry in the local ``pyproject.toml`` file
    named ``tool.lsst_versions`` and the key ``write_to`` should
    be used to specify where the version information should be written.

    Will do nothing if no TOML file can be found.
    """
    if not os.path.isfile("pyproject.toml"):
        return

    if tomli is None:
        warnings.warn(  # type: ignore
            "The tomli package is not installed. " "Unable to extract version file location."
        )
        return

    with open("pyproject.toml") as fh:
        parsed = tomli.loads(fh.read())

    try:
        tool = parsed["tool"]["lsst_versions"]
    except KeyError:
        # No valid tool entry so nothing to do.
        return

    write_to = tool.get("write_to")
    if not write_to:
        warnings.warn("lsst_versions package enabled but no write_to setting found in pyproject.toml.")
        return

    # Find the version of HEAD and current directory.
    version = find_dev_lsst_version(".", "HEAD")
    _write_version(version, write_to)

    dist.metadata.version = version
