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

__all__ = ["find_lsst_version", "get_lsst_version", "infer_version_for_setuptools"]

import contextlib
import logging
import os
import re
import tomllib
import warnings
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import git
from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    import setuptools

_LOG = logging.getLogger("lsst_versions")

# Environment variable that overrides the log level used while another
# package is being built.
_LOG_LEVEL_ENV = "LSST_VERSIONS_LOG_LEVEL"


@contextlib.contextmanager
def _build_logging() -> Iterator[None]:
    """Restrict logging from this package while another package is built.

    Yields
    ------
    `None`
        A context in which this package logs at ``INFO`` or above.

    Notes
    -----
    The build system plugins run inside the build of some other package and
    a debug message is issued for every tag in that package's Git
    repository. A repository with many tags therefore buries the build
    system's own output. The single informational message reporting the
    chosen version is retained. The level can be changed by setting the
    ``LSST_VERSIONS_LOG_LEVEL`` environment variable.
    """
    previous = _LOG.level
    _LOG.setLevel(os.environ.get(_LOG_LEVEL_ENV, "INFO").upper())
    try:
        yield
    finally:
        _LOG.setLevel(previous)


def _guess_next_version(version: Version) -> str:
    """Guess the release that will follow the given release.

    Parameters
    ----------
    version : `packaging.version.Version`
        The release to base the guess on.

    Returns
    -------
    guessed : `str`
        The release expected to follow ``version``.

    Notes
    -----
    This implements the ``guess-next-dev`` version scheme defined by
    ``setuptools_scm``, so that this package can follow the same convention
    without depending on it. Any local segment is discarded, a tag that is
    itself a ``.dev0`` placeholder resolves to the release it names, and
    otherwise the trailing number is incremented. ``1.6.0`` therefore becomes
    ``1.6.1`` and ``3.0.0rc1`` becomes ``3.0.0rc2``.
    """
    # A local segment says nothing about the next release.
    public = str(version).partition("+")[0]

    if ".dev" in public:
        # A development tag is a placeholder for the release it names, so
        # that release is the answer rather than the one after it.
        prefix, _, tail = public.rpartition(".dev")
        if tail != "0":
            # As in setuptools_scm: the distance counted from such a tag
            # would conflict with the number already in it.
            raise ValueError(f"Unsupported development release tag {public}; only .dev0 can be used.")
        return prefix

    if (matched := re.match(r"(.*?)(\d+)$", public)) is None:
        raise ValueError(f"Unable to guess the release following {public}; it does not end in a number.")

    prefix, tail = matched.groups()
    return f"{prefix}{int(tail) + 1}"


def _find_semver_dev_version(
    repo: git.Repo,
    commit: git.objects.commit.Commit,
    releases: dict[str, Version],
    repo_dir: str | os.PathLike[str],
) -> str:
    """Derive a development version for a repository without weekly tags.

    Parameters
    ----------
    repo : `git.Repo`
        The repository being inspected.
    commit : `git.objects.commit.Commit`
        The commit that the version is being calculated for.
    releases : `dict` [ `str`, `packaging.version.Version` ]
        Versions of every release tag in the repository, indexed by the
        hex SHA of the commit that the tag refers to.
    repo_dir : `str` or `os.PathLike`
        Path to the repository, used for diagnostics.

    Returns
    -------
    dev_version : `str`
        The release expected to follow the most recent release reachable
        from ``commit``, with a PEP 440 development segment counting the
        commits made since that release.

    Notes
    -----
    This is the ``guess-next-dev`` scheme used by ``setuptools_scm``. A tree
    22 commits after ``1.6.0`` is ``1.6.1.dev22``, which sorts above
    ``1.6.0`` and below ``1.6.1``.
    """
    # The most recent release is the highest version whose tagged commit is
    # in the history of the commit being versioned. Tags on unrelated
    # branches are therefore ignored.
    ancestors: list[tuple[Version, str]] = []
    for hexsha, version in releases.items():
        if repo.is_ancestor(repo.commit(hexsha), commit):
            ancestors.append((version, hexsha))

    if ancestors:
        base, release_hexsha = max(ancestors, key=lambda entry: entry[0])
        commit_range = f"{release_hexsha}..{commit.hexsha}"
    else:
        warnings.warn(
            f"Could not find release tag as ancestor for {commit} in repo '{repo_dir}', using 0.0.0."
        )
        base = Version("0.0.0")
        commit_range = commit.hexsha

    # Distance from the release to this commit, matching the count reported
    # by "git describe".
    distance = int(repo.git.rev_list("--count", commit_range))

    dev_version = str(Version(f"{_guess_next_version(base)}.dev{distance}"))

    _LOG.info("Using version %s for commit %s derived from release %s", dev_version, commit.hexsha, base)

    return dev_version


def find_lsst_version(repo_dir: str | os.PathLike[str] = ".", version_commit: str = "HEAD") -> str:
    """Return the version for the given LSST commit.

    Parameters
    ----------
    repo_dir : `str` or `os.PathLike`, optional
        Path to the relevant Git repository.
    version_commit : `str`, optional
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
    #. The number of commits from this commit to the closest weekly tag,
       ``CC``.
    #. Creating a new version of ``NN.YYYY.WWCC``.

    If a commit matches that of a formal release tag (either proper release
    or release candidate) that version is used directly.

    Repositories that have no weekly tags at all are versioned by semantic
    versioning instead, following the ``guess-next-dev`` scheme used by
    ``setuptools_scm``: the release expected to follow the most recent release
    tag reachable from the commit, with a PEP 440 development segment counting
    the commits made since that tag. A tree 22 commits after ``1.6.0`` is
    therefore ``1.6.1.dev22``.
    """
    repo = git.Repo(repo_dir)

    releases: dict[str, Version] = {}
    major_releases: dict[int, git.objects.commit.Commit] = {}
    weeklies: dict[str, str] = {}

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

    if not weeklies:
        # The repository does not follow the LSST weekly tagging convention
        # so there is nothing to encode a year and week from.
        return _find_semver_dev_version(repo, commit, releases, repo_dir)

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
    optional_commit: git.objects.commit.Commit | None = commit
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

    # Declare the developer version to be an evolution of the current
    # release but with the year and week in the minor and patchlevel parts.
    # Alpha versions for weeklies were used initially but once full releases
    # are made it becomes very difficult for tooling to ever install the
    # alphas.
    dev_version = f"{relevant_release}.{year}.{week}{counter:02d}"

    # Convert the version to standard form (this can prevent warnings
    # coming from setuptools later on). For example 1.0.0a07 is rewritten
    # as 1.0.0a7.
    dev_version = str(Version(dev_version))

    _LOG.info(
        "Using version %s for commit %s derived from weekly %s", dev_version, commit.hexsha, weekly_name
    )

    return dev_version


def _write_version(version: str, version_path: str | os.PathLike[str]) -> None:
    """Write the version information to the specified file."""
    Path(version_path).write_text(
        f"""__all__ = ["__version__"]
__version__ = "{version}"
"""
    )


def _find_version_path(dirname: str | os.PathLike[str] = ".") -> Path | None:
    """Find the path to the python version file.

    Uses the ``pyproject.toml`` file in the given directory.

    Parameters
    ----------
    dirname : `str` or `os.PathLike`, optional
        The directory to locate the ``pyproject.toml`` file.

    Returns
    -------
    path : `pathlib.Path` or `None`
        The path (including ``dir``) to the version file. Returns ``None``
        if the path could not be determined.
    """
    path = Path(dirname) / "pyproject.toml"
    if not path.is_file():
        warnings.warn(f"No pyproject.toml file found in {dirname}.")
        return None

    parsed = tomllib.loads(path.read_text())

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

    return Path(dirname) / write_to


def _find_version_from_pkginfo(dirname: str | os.PathLike[str] = ".") -> str | None:
    """Find version information from PKG-INFO file.

    Parameters
    ----------
    dirname : `str` or `os.PathLike`
        The directory of the distribution.

    Returns
    -------
    version : `str` or `None`
        The version string. `None` if no version can be found.
    """
    pkginfo = Path(dirname) / "PKG-INFO"
    if not pkginfo.exists():
        return None

    content: dict[str, str] = {}
    with pkginfo.open() as fh:
        for line in fh:
            if ": " in line:
                line = line.strip()
                k, v = line.split(": ", 1)
                content[k] = v
    return content.get("Version", None)


def _find_version_from_egg_info(dirname: str | os.PathLike[str] = ".") -> str | None:
    """Find version information from egg-info directory.

    This is a fallback situation when no Git repository is available.

    Parameters
    ----------
    dirname : `str` or `os.PathLike`
        The directory of the distribution.

    Returns
    -------
    version : `str` or `None`
        The version string. `None` if no version can be found.

    Notes
    -----
    Looks for an egg-info directory in the current directory and also in the
    standard ``python`` directory.
    Does not look at pyproject.toml for tool.setuptools.packages.find.where.
    """
    root = Path(dirname)
    for candidate in (root / "python", root):
        if not candidate.is_dir():
            continue
        for entry in candidate.iterdir():
            if entry.name.endswith(".egg-info"):
                version = _find_version_from_pkginfo(entry)
                if version is not None:
                    return version
                break

    return None


def _find_version_from_metadata(dirname: str | os.PathLike[str] = ".") -> str | None:
    """Find version information from package metadata.

    This is a fallback situation when no Git repository is available.

    Parameters
    ----------
    dirname : `str` or `os.PathLike`
        The directory of the distribution.

    Returns
    -------
    version : `str` or `None`
        The version string. `None` if no version can be found.
    """
    version = _find_version_from_pkginfo(dirname)
    if version is not None:
        return version
    version = _find_version_from_egg_info(dirname)
    return version


def _process_version_writing(
    dirname: str | os.PathLike[str] = ".", write_version: bool = True, fallback: bool = False
) -> tuple[str, Path | None]:
    """Determine the version and, optionally, write it.

    Parameters
    ----------
    dirname : `str` or `os.PathLike`
        The directory to use to find a version.
    write_version : `bool`
        If `True`, an attempt will be made to write the version file.
        This will fail if no valid ``pyproject.toml`` file can be found
        in ``dir``.
    fallback : `bool`, optional
        If `True` and no Git version can be found, an attempt will be made
        to find the version from package metadata. This can be important
        for source distributions that are no longer part of a Git repository.

    Returns
    -------
    version : `str`
        The version string.
    written : `pathlib.Path`, optional
        Path to the file that was written, or `None` if no version file was
        written.
    """
    # Find the version file in current working directory.
    write_to: Path | None = None
    written = None
    if write_version:
        write_to = _find_version_path(dirname)
        if write_to is None:
            return "<unknown>", written

    # Find the version of HEAD and current directory.
    version = get_lsst_version(dirname, fallback)

    if write_version and write_to:
        _write_version(version, write_to)

    return version, write_to


def get_lsst_version(dirname: str | os.PathLike[str] = ".", fallback: bool = True) -> str:
    """Determine the version and return as string

    Parameters
    ----------
    dirname : `str` or `os.PathLike`, optional
        The directory to use to find a version.
    fallback : `bool`, optional
        If `True` and no Git version can be found, an attempt will be made
        to find the version from package metadata. This can be important
        for source distributions that are no longer part of a Git repository.

    Returns
    -------
    version : `str`
        The version string.

    This function returns the HEAD version of a direcotry
    """
    version: str | None = None
    try:
        version = find_lsst_version(dirname, "HEAD")
    except Exception:
        if not fallback:
            raise
    if version is None:
        version = _find_version_from_metadata(dirname)
        if version is None:
            raise RuntimeError(f"Unable to find a version from Git or metadata within directory {dirname}")
    return version


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

    If Git can not be used, an attempt will be made to read a PKG-INFO
    file. This allows source-only distributions to be built.

    Debug logging from this package is suppressed so that it does not
    obscure the output of the build that triggered it. Set the
    ``LSST_VERSIONS_LOG_LEVEL`` environment variable to see it.
    """
    with _build_logging():
        version, written = _process_version_writing(".", True, fallback=True)
    if not written:
        return

    dist.metadata.version = version
