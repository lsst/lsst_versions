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

"""Fixtures shared by the lsst_versions tests."""

import tarfile
from pathlib import Path

import git
import pytest

TESTDIR = Path(__file__).absolute().parent


@pytest.fixture(scope="session")
def testdir() -> Path:
    """Return the directory containing the tests."""
    return TESTDIR


@pytest.fixture(scope="session")
def datadir(testdir: Path) -> Path:
    """Return the directory containing the static test data."""
    return testdir / "data"


@pytest.fixture(scope="session")
def gitdir(testdir: Path) -> Path:
    """Return the test Git repository, unpacking it if necessary.

    The repository is stored as a tar file so that it is not a Git
    repository nested inside this one.
    """
    repo = testdir / "repo"
    if not repo.exists():
        with tarfile.open(testdir / "test-repo.tgz", "r:gz") as tar:
            if hasattr(tarfile, "data_filter"):
                tar.extractall(path=testdir, filter="data")
            else:
                # Remove when minimum test matrix python >= 3.12
                tar.extractall(path=testdir)

    # The version writing tests need a pyproject.toml in the repository.
    pyproject = repo / "pyproject.toml"
    if not pyproject.exists():
        pyproject.symlink_to(testdir / "test_pyproject.toml")

    try:
        git.Repo(repo)
    except Exception:
        pytest.skip("Git repository for this package is not accessible.")

    return repo
