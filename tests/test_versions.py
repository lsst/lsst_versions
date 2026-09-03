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

import os
import sys
import tarfile
import tempfile
import unittest

import git
from lsst_versions import find_lsst_version, get_lsst_version

# Also need an internal function to test the lsst-versions command.
from lsst_versions._cmd import _run_command as run_lsst_versions

# And to check pyproject.toml parsing and PKG-INFO parsing.
from lsst_versions._versions import _find_version_path as find_version_path
from lsst_versions._versions import _guess_next_version as guess_next_version
from lsst_versions._versions import _process_version_writing as process_version_writing
from packaging.version import Version

TESTDIR = os.path.abspath(os.path.dirname(__file__))
GITDIR = os.path.join(TESTDIR, "repo")
TARFILE = os.path.join(TESTDIR, "test-repo.tgz")


def setup_module(module):
    """Ensure that the test git repository is present.

    This repository is stored as a tar file and must be unpacked
    before the tests run.
    """
    if not os.path.exists(GITDIR):
        with tarfile.open(TARFILE, "r:gz") as tar:
            if hasattr(tarfile, "data_filter"):
                tar.extractall(path=TESTDIR, filter="data")
            else:
                # Remove when minimum test matrix python >= 3.12
                tar.extractall(path=TESTDIR)

    # Ensure that the pyproject.toml file is in the test directory.
    target = os.path.join(GITDIR, "pyproject.toml")
    if not os.path.exists(target):
        os.symlink(os.path.join(TESTDIR, "test_pyproject.toml"), target)


class VersionsTestCase(unittest.TestCase):
    """Test Git version finding."""

    def setUp(self):
        try:
            git.Repo(GITDIR)
        except Exception:
            raise unittest.SkipTest("Git repository for this package is not accessible.")

    def test_get_lsst_version(self):
        # test get_lsst_version which returns version for the current directory
        datadir = os.path.join(TESTDIR, "data")
        # test for directory with package info
        dirname = os.path.join(datadir, "something.egg-info")
        version = get_lsst_version(dirname)
        self.assertEqual(version, "1.1.0")
        # test for git repo
        version = get_lsst_version(GITDIR)
        self.assertEqual(version, "3.2022.1037")
        # test for pyproject
        dirname = os.path.join(datadir, "pyproject")
        version = get_lsst_version(dirname)
        self.assertEqual(version, "3.4.0a32")

    def test_versions(self):
        """Determine versions of a test repository."""
        versions = (
            ("86427e5", "0.0.0"),  # No parents
            ("86b5d01", "0.0.1"),
            ("595e858", "1.0"),
            ("ea28756", "1.2022.400"),
            ("af0c308", "1.2022.100"),
            ("w.2022.1", "1.2022.100"),
            ("da7a09d", "1.2022.401"),
            ("v2.1.0", "2.1.0"),
            ("w.2022.05", "1.2022.700"),
            ("v3.0.0", "3.0.0"),
            ("3082cf0", "3.2022.1001"),
            ("fed5a45", "3.0.0rc2"),
        )

        for tag, expected in versions:
            # Check that we get a warning when no release tag ancestor.
            if expected.startswith("1.0.0a"):
                with self.assertWarns(UserWarning) as cm:
                    version = find_lsst_version(GITDIR, tag)
                self.assertIn("Could not find release tag", str(cm.warning))
            else:
                version = find_lsst_version(GITDIR, tag)
            with self.subTest(tag=tag, expected=expected):
                self.assertEqual(version, expected)

    def test_version_writing(self):
        """Test that a version file can be written."""
        version_file = "version_test.py"
        version_path = os.path.join(GITDIR, version_file)
        try:
            os.remove(version_path)
        except FileNotFoundError:
            pass

        # Look where there is no pyproject file.
        with self.assertLogs("lsst_versions", level="INFO") as cm:
            with self.assertWarns(UserWarning):
                version = run_lsst_versions(TESTDIR, True)
        self.assertEqual(version, "<unknown>")
        self.assertIn("Unable to write version file.", cm.output[-1])

        # Find a version but do not write.
        version = run_lsst_versions(GITDIR, False)
        self.assertEqual(version, "3.2022.1037")
        self.assertFalse(os.path.exists(version_path))

        # Now write the file.
        with self.assertLogs("lsst_versions", level="INFO") as cm:
            version = run_lsst_versions(GITDIR, True)
        self.assertEqual(len(cm.output), 3, cm.output)
        self.assertRegex(cm.output[-1], f"Written version file to .*{version_file}$")
        self.assertEqual(version, "3.2022.1037")
        self.assertTrue(os.path.exists(version_path))

    def test_pyproject_finding(self):
        """Test that we can find failure modes in pyproject.toml."""
        datadir = os.path.join(TESTDIR, "data")

        with self.assertWarns(UserWarning) as cm:
            path = find_version_path(os.path.join(datadir, "no-pyproject"))
        self.assertIsNone(path)
        self.assertIn("No pyproject.toml", str(cm.warning))

        with self.assertWarns(UserWarning) as cm:
            path = find_version_path(os.path.join(datadir, "pyproject"))
        self.assertIsNone(path)
        self.assertIn("entry not found", str(cm.warning))

        with self.assertWarns(UserWarning) as cm:
            path = find_version_path(os.path.join(datadir, "no-write-pyproject"))
        self.assertIsNone(path)
        self.assertIn("no write_to setting", str(cm.warning))

    def test_fallback_version(self):
        """Test that fallback to PKG-INFO works correctly."""
        datadir = os.path.join(TESTDIR, "data")

        # A directory that does have an egg-info but no git and no fallback.
        with self.assertRaises(Exception):
            process_version_writing(datadir, write_version=False, fallback=False)

        # Directory with an egg-info.
        version, _ = process_version_writing(datadir, write_version=False, fallback=True)
        self.assertEqual(version, "1.1.0")

        # Directory with a PKG-INFO.
        version, _ = process_version_writing(
            os.path.join(datadir, "something.egg-info"), write_version=False, fallback=True
        )
        self.assertEqual(version, "1.1.0")

        # Directory with a python directory that has an egg-info in it.
        version, _ = process_version_writing(
            os.path.join(datadir, "pyproject"), write_version=False, fallback=True
        )
        self.assertEqual(version, "3.4.0a32")

        # Fallback allowed but no PKG-INFO.
        with self.assertRaises(RuntimeError):
            process_version_writing(os.path.join(datadir, "no-pyproject"), write_version=False, fallback=True)


class SemanticVersionTestCase(unittest.TestCase):
    """Test version finding for repositories that have no weekly tags."""

    def setUp(self):
        self.tmpdir = self.enterContext(tempfile.TemporaryDirectory())
        self.repo = git.Repo.init(self.tmpdir)
        with self.repo.config_writer() as config:
            config.set_value("user", "name", "lsst_versions test")
            config.set_value("user", "email", "test@example.com")
            # Signing would need a key that the test environment does not have.
            config.set_value("commit", "gpgsign", "false")

    def commit(self, message):
        """Add an empty commit to the test repository."""
        self.repo.index.commit(message)

    def test_release_tag(self):
        """A commit that is itself tagged uses that version directly."""
        self.commit("Initial commit")
        self.repo.create_tag("1.0.0")
        self.assertEqual(find_lsst_version(self.tmpdir), "1.0.0")

    def test_dev_version(self):
        """Commits after a release count towards the following release."""
        self.commit("Initial commit")
        self.repo.create_tag("1.0.0")
        self.commit("Development")
        self.repo.create_tag("v1.6.0")
        for i in range(3):
            self.commit(f"Development {i}")
        self.assertEqual(find_lsst_version(self.tmpdir), "1.6.1.dev3")

    def test_release_candidate(self):
        """The number bumped is the trailing one, so an rc bumps the rc."""
        self.commit("Initial commit")
        self.repo.create_tag("v3.0.0rc1")
        self.commit("Development")
        self.assertEqual(find_lsst_version(self.tmpdir), "3.0.0rc2.dev1")

    def test_highest_release_wins(self):
        """A later tag with a lower version does not move the version back."""
        self.commit("Initial commit")
        self.repo.create_tag("1.6.0")
        self.commit("Backport")
        self.repo.create_tag("1.2.0")
        self.commit("Development")
        self.assertEqual(find_lsst_version(self.tmpdir), "1.6.1.dev2")

    def test_no_release_tags(self):
        """A repository with no tags at all still gets a usable version."""
        self.commit("Initial commit")
        self.commit("Development")
        with self.assertWarns(UserWarning) as cm:
            version = find_lsst_version(self.tmpdir)
        self.assertIn("Could not find release tag", str(cm.warning))
        self.assertEqual(version, "0.0.1.dev2")


class GuessNextVersionTestCase(unittest.TestCase):
    """Test the ``setuptools_scm`` guess-next-dev version calculation."""

    def test_guesses(self):
        guesses = (
            ("1.6.0", "1.6.1"),
            ("1.6", "1.7"),
            ("3.0.0rc1", "3.0.0rc2"),
            ("1.0.0a7", "1.0.0a8"),
            ("1.0.0.post1", "1.0.0.post2"),
            # A local segment says nothing about the next release.
            ("1.0.0+g1234abc", "1.0.1"),
            # A development tag names the release it is a placeholder for.
            ("2.0.0.dev0", "2.0.0"),
        )
        for version, expected in guesses:
            with self.subTest(version=version):
                self.assertEqual(guess_next_version(Version(version)), expected)

    def test_unsupported_dev_tag(self):
        with self.assertRaises(ValueError):
            guess_next_version(Version("2.0.0.dev1"))


if __name__ == "__main__":
    setup_module(sys.modules[__name__])
    unittest.main()
