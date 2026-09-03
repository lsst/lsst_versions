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

"""Tests of the version calculation itself."""

import logging
import re
from pathlib import Path

import git
import pytest
from lsst_versions import find_lsst_version, get_lsst_version

# Also need an internal function to test the lsst-versions command.
from lsst_versions._cmd import _run_command as run_lsst_versions

# And to check pyproject.toml parsing and PKG-INFO parsing.
from lsst_versions._versions import _find_version_path as find_version_path
from lsst_versions._versions import _guess_next_version as guess_next_version
from lsst_versions._versions import _process_version_writing as process_version_writing
from packaging.version import Version


def messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Return the messages this package logged, ignoring other loggers."""
    return [record.getMessage() for record in caplog.records if record.name == "lsst_versions"]


@pytest.mark.parametrize(
    ("parts", "expected"),
    (
        (("something.egg-info",), "1.1.0"),
        (("pyproject",), "3.4.0a32"),
    ),
)
def test_get_lsst_version_from_metadata(datadir: Path, parts: tuple[str, ...], expected: str) -> None:
    """A directory with package metadata reports the recorded version."""
    assert get_lsst_version(datadir.joinpath(*parts)) == expected


def test_get_lsst_version_from_git(gitdir: Path) -> None:
    """A Git repository reports a version derived from its tags."""
    assert get_lsst_version(gitdir) == "3.2022.1037"


@pytest.mark.parametrize(
    ("committish", "expected", "warns"),
    (
        # The first two commits have no release tag as an ancestor.
        ("86427e5", "0.0.0", True),  # No parents
        ("86b5d01", "0.0.1", True),
        ("595e858", "1.0", False),
        ("ea28756", "1.2022.400", False),
        ("af0c308", "1.2022.100", False),
        ("w.2022.1", "1.2022.100", False),
        ("da7a09d", "1.2022.401", False),
        ("v2.1.0", "2.1.0", False),
        ("w.2022.05", "1.2022.700", False),
        ("v3.0.0", "3.0.0", False),
        ("3082cf0", "3.2022.1001", False),
        ("fed5a45", "3.0.0rc2", False),
    ),
)
def test_versions(gitdir: Path, committish: str, expected: str, warns: bool) -> None:
    """Determine versions of a test repository."""
    if warns:
        with pytest.warns(UserWarning, match="Could not find release tag"):
            version = find_lsst_version(gitdir, committish)
    else:
        version = find_lsst_version(gitdir, committish)
    assert version == expected


def test_version_writing(testdir: Path, gitdir: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that a version file can be written."""
    version_path = gitdir / "version_test.py"
    version_path.unlink(missing_ok=True)

    # Look where there is no pyproject file.
    with caplog.at_level(logging.INFO, logger="lsst_versions"):
        with pytest.warns(UserWarning):
            version = run_lsst_versions(testdir, True)
    assert version == "<unknown>"
    assert "Unable to write version file." in messages(caplog)[-1]

    # Find a version but do not write.
    assert run_lsst_versions(gitdir, False) == "3.2022.1037"
    assert not version_path.exists()

    # Now write the file.
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="lsst_versions"):
        version = run_lsst_versions(gitdir, True)
    logged = messages(caplog)
    assert len(logged) == 3, logged
    assert re.search(f"Written version file to .*{version_path.name}$", logged[-1])
    assert version == "3.2022.1037"
    assert version_path.exists()


@pytest.mark.parametrize(
    ("subdir", "message"),
    (
        ("no-pyproject", "No pyproject.toml"),
        ("pyproject", "entry not found"),
        ("no-write-pyproject", "no write_to setting"),
    ),
)
def test_pyproject_finding(datadir: Path, subdir: str, message: str) -> None:
    """Test that we can find failure modes in pyproject.toml."""
    with pytest.warns(UserWarning, match=message):
        assert find_version_path(datadir / subdir) is None


@pytest.mark.parametrize(
    ("parts", "expected"),
    (
        ((), "1.1.0"),  # Directory containing an egg-info.
        (("something.egg-info",), "1.1.0"),
        (("pyproject",), "3.4.0a32"),  # egg-info inside a python directory.
    ),
)
def test_fallback_version(datadir: Path, parts: tuple[str, ...], expected: str) -> None:
    """Test that fallback to PKG-INFO works correctly."""
    version, _ = process_version_writing(datadir.joinpath(*parts), write_version=False, fallback=True)
    assert version == expected


def test_fallback_not_allowed(datadir: Path) -> None:
    """Without a fallback the Git failure is reported as-is."""
    with pytest.raises(git.InvalidGitRepositoryError):
        process_version_writing(datadir, write_version=False, fallback=False)


def test_fallback_without_metadata(datadir: Path) -> None:
    """A fallback still fails when there is no metadata to fall back to."""
    with pytest.raises(RuntimeError, match="Unable to find a version"):
        process_version_writing(datadir / "no-pyproject", write_version=False, fallback=True)


@pytest.fixture
def semver_repo(tmp_path: Path) -> git.Repo:
    """Return an empty Git repository that uses no weekly tags."""
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "lsst_versions test")
        config.set_value("user", "email", "test@example.com")
        # Signing would need a key that the test environment does not have.
        config.set_value("commit", "gpgsign", "false")
    return repo


def commit(repo: git.Repo, message: str) -> None:
    """Add an empty commit to the given repository."""
    repo.index.commit(message)


def test_release_tag(semver_repo: git.Repo, tmp_path: Path) -> None:
    """A commit that is itself tagged uses that version directly."""
    commit(semver_repo, "Initial commit")
    semver_repo.create_tag("1.0.0")
    assert find_lsst_version(tmp_path) == "1.0.0"


def test_dev_version(semver_repo: git.Repo, tmp_path: Path) -> None:
    """Commits after a release count towards the following release."""
    commit(semver_repo, "Initial commit")
    semver_repo.create_tag("1.0.0")
    commit(semver_repo, "Development")
    semver_repo.create_tag("v1.6.0")
    for i in range(3):
        commit(semver_repo, f"Development {i}")
    assert find_lsst_version(tmp_path) == "1.6.1.dev3"


def test_release_candidate(semver_repo: git.Repo, tmp_path: Path) -> None:
    """The number bumped is the trailing one, so an rc bumps the rc."""
    commit(semver_repo, "Initial commit")
    semver_repo.create_tag("v3.0.0rc1")
    commit(semver_repo, "Development")
    assert find_lsst_version(tmp_path) == "3.0.0rc2.dev1"


def test_highest_release_wins(semver_repo: git.Repo, tmp_path: Path) -> None:
    """A later tag with a lower version does not move the version back."""
    commit(semver_repo, "Initial commit")
    semver_repo.create_tag("1.6.0")
    commit(semver_repo, "Backport")
    semver_repo.create_tag("1.2.0")
    commit(semver_repo, "Development")
    assert find_lsst_version(tmp_path) == "1.6.1.dev2"


def test_no_release_tags(semver_repo: git.Repo, tmp_path: Path) -> None:
    """A repository with no tags at all still gets a usable version."""
    commit(semver_repo, "Initial commit")
    commit(semver_repo, "Development")
    with pytest.warns(UserWarning, match="Could not find release tag"):
        assert find_lsst_version(tmp_path) == "0.0.1.dev2"


@pytest.mark.parametrize(
    ("version", "expected"),
    (
        ("1.6.0", "1.6.1"),
        ("1.6", "1.7"),
        ("3.0.0rc1", "3.0.0rc2"),
        ("1.0.0a7", "1.0.0a8"),
        ("1.0.0.post1", "1.0.0.post2"),
        # A local segment says nothing about the next release.
        ("1.0.0+g1234abc", "1.0.1"),
        # A development tag names the release it is a placeholder for.
        ("2.0.0.dev0", "2.0.0"),
    ),
)
def test_guess_next_version(version: str, expected: str) -> None:
    """Check the guess-next-dev calculation against known releases."""
    assert guess_next_version(Version(version)) == expected


def test_guess_next_version_unsupported_dev_tag() -> None:
    """A development tag numbered above zero cannot be bumped."""
    with pytest.raises(ValueError, match="only .dev0 can be used"):
        guess_next_version(Version("2.0.0.dev1"))
