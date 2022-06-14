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

__all__ = ["find_lsst_version", "infer_version_for_setuptools"]

import logging
import os
import re
import warnings
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from packaging.version import InvalidVersion, Version

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


_LOG = logging.getLogger("lsst_versions")


def find_lsst_version(repo_dir: str, version_commit: str) -> str:
    """Return the version for the given LSST commit.

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

    If a commit matches that of a formal release tag (either proper release
    or release candidate) that version is used directly.
    """
    if git is None:
        raise RuntimeError("GitPython package not installed. Unable to determine version.")

    repo = git.Repo(repo_dir)

    releases: Dict[str, Version] = {}
    major_releases: Dict[int, git.objects.commit.Commit] = {}
    weeklies: Dict[str, str] = {}

    for tagref in repo.tags:
        tag_name = str(tagref)
        _LOG.debug("Testing relevance of tag %s", tag_name)
        # LSST repos have release versions as either x.y.z version
        # strings of vx.y.z (with optional rc numbers).
        # Extract major version numbers from these and also store them
        # in case the requested commit is actually associated with
        # a full release.
        if matches_release := re.match(r"v?(\d+.*)", tag_name):
            _LOG.debug("Tag %s matches a release.", tag_name)

            version_string = matches_release.group(1)
            # Assume the version string is parseable as a modern
            # version. Some packages have odd (old) tags like 2015_10.0
            # or 6.2-hsc, so skip those as not being relevant.
            try:
                parsed = Version(version_string)
            except InvalidVersion:
                _LOG.info("Version string rejected: %s", version_string)
                continue

            # Get the relevant commit from the tag.
            release = tagref.tag
            if release is None:
                # Assume a lightweight tag, so the commit is what
                # we have to use.
                release_commit = tagref.commit
            else:
                release_commit = release.object

            hexsha = release_commit.hexsha
            if hexsha in releases:
                # This commit already has a version number associated with
                # it. Check if this current version is newer and if so
                # replace it.
                if parsed > releases[hexsha]:
                    releases[hexsha] = parsed
            else:
                releases[hexsha] = parsed

            # Assume that only major releases matter when looking through
            # the history for developer versions.
            major_releases[int(parsed.major)] = release_commit
        elif tag_name.startswith("w."):
            _LOG.debug("Tag %s matches a weekly", tag_name)
            weekly = tagref.tag
            if weekly is None:
                # Lightweight tag.
                weekly_commit = tagref.commit
            else:
                weekly_commit = weekly.object

            # There can be multiple weeklies associated with a single
            # commit. Retain the newest weekly. Some weekly tags did not
            # zero pad the week so must be normalized before comparison.
            if len(tag_name) == 8:
                tag_name = f"{tag_name[:7]}0{tag_name[-1]}"

            # Store the weeklies associated with the object they are tagging
            # but only if this weekly is more recent than the one that may
            # already be stored.
            hexsha = weekly_commit.hexsha
            if (previous := weeklies.get(hexsha, None)) and previous > tag_name:
                continue
            weeklies[hexsha] = tag_name

    commit = repo.commit(version_commit)

    # if this commit is actually a valid release, use that directly.
    if (hexsha := commit.hexsha) in releases:
        _LOG.debug("Requested commit %s matches release %s.", commit.hexsha, releases[hexsha])
        return str(releases[hexsha])

    # Scan through all the releases for the first that does not have this
    # commit as an ancestor.
    relevant_release = 0
    for major_release in sorted(major_releases, reverse=True):
        major_commit = major_releases[major_release]
        if not repo.is_ancestor(commit, major_commit):
            relevant_release = major_release
            break

    if relevant_release == 0:
        warnings.warn(f"Could not find release tag as ancestor for {commit} in repo '{repo_dir}', using 0.")

    # Look through the parents until we find a weekly commit.
    # The counter can report confusing results if this is being used for
    # an unmerged development branch (and on GitHub a pull request will
    # include an extra commit because it merges the branch for testing).
    counter = -1
    weekly_name = ""
    optional_commit: Optional[git.objects.commit.Commit] = commit
    while optional_commit:
        counter += 1
        if (hexsha := optional_commit.hexsha) in weeklies:
            weekly_name = weeklies[hexsha]
            break
        parents = optional_commit.parents
        optional_commit = parents[0] if parents else None

    if not weekly_name:
        # No weekly was found. This must be a very early commit.
        year, week = "0", "0"
    else:
        year, week = weekly_name[2:].split(".")

    # Python pre-release versions must can only have a single integer
    # after the "a".
    dev_version = f"{relevant_release + 1}.0.0a{int(year):04d}{int(week):02d}{counter:02d}"

    # Convert the version to standard form (this can prevent warnings
    # coming from setuptools later on). For example 1.0.0a07 is rewritten
    # as 1.0.0a7.
    dev_version = str(Version(dev_version))

    _LOG.info(
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


def _find_version_path(dir: str = ".") -> Optional[str]:
    """Find the path to the python version file.

    Uses the ``pyproject.toml`` file in the given directory.

    Parameters
    ----------
    dir : `str`, optional
        The directory to locate the ``pyproject.toml`` file.

    Returns
    -------
    path : `str` or `None`
        The path (including ``dir``) to the version file. Returns ``None``
        if the path could not be determined.
    """
    path = os.path.join(dir, "pyproject.toml")
    if not os.path.isfile(path):
        warnings.warn(f"No pyproject.toml file found in {dir}.")
        return None

    if tomli is None:
        warnings.warn(  # type: ignore
            "The tomli package is not installed. " "Unable to extract version file location."
        )
        return None

    with open(path) as fh:
        parsed = tomli.loads(fh.read())

    try:
        tool = parsed["tool"]["lsst_versions"]
    except KeyError:
        # No valid tool entry so nothing to do.
        warnings.warn(f"[tool.lsst_versions] entry not found in pyproject.toml at {path}")
        return None

    write_to = tool.get("write_to")
    if not write_to:
        warnings.warn("lsst_versions package enabled but no write_to setting found in pyproject.toml.")
        return None

    return os.path.join(dir, write_to)


def _process_version_writing(dir: str = ".", write_version: bool = True) -> Tuple[str, Optional[str]]:
    """Determine the version and, optionally, write it.

    Parameters
    ----------
    dir : `str`
        The directory to use to find a version.
    write_version : `bool`
        If `True`, an attempt will be made to write the version file.
        This will fail if no valid ``pyproject.toml`` file can be found
        in ``dir``.

    Returns
    -------
    version : `str`
        The version string.
    written : `str`, optional
        Path to the file that was written, or `None` if no version file was
        written.
    """
    # Find the version file in current working directory.
    write_to: Optional[str] = None
    written = None
    if write_version:
        write_to = _find_version_path(dir)
        if write_to is None:
            return "<unknown>", written

    # Find the version of HEAD and current directory.
    version = find_lsst_version(dir, "HEAD")
    if write_version and write_to:
        _write_version(version, write_to)

    return version, write_to


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
    version, written = _process_version_writing(".", True)
    if not written:
        return

    dist.metadata.version = version
