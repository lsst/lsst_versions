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
import unittest

try:
    import git
except ImportError:
    git = None

from lsst_versions import find_dev_lsst_version

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
            tar.extractall(path=TESTDIR)


@unittest.skipIf(git is None, "GitPython package is not installed.")
class VersionsTestCase(unittest.TestCase):
    """Test Git version finding."""

    def setUp(self):
        try:
            git.Repo(GITDIR)
        except Exception:
            raise unittest.SkipTest("Git repository for this package is not accessible.")

    def test_versions(self):
        """Determine versions of a test repository."""
        versions = (
            ("86b5d01", "1.0.0a00000001"),  # v1.0
            ("ea28756", "2.0.0a20220400"),
            ("af0c308", "2.0.0a20220100"),
            ("w.2022.1", "2.0.0a20220100"),
            ("da7a09d", "2.0.0a20220401"),
            ("v2.1.0", "2.0.0a20220900"),  # Should be 2.1.0
            ("w.2022.05", "2.0.0a20220600"),
            ("v3.0.0", "3.0.0a20220903"),
            ("3082cf0", "4.0.0a20221001"),
        )

        for tag, expected in versions:
            version = find_dev_lsst_version(GITDIR, tag)
            with self.subTest(tag=tag, expected=expected):
                self.assertEqual(version, expected)


if __name__ == "__main__":
    setup_module(sys.modules[__name__])
    unittest.main()
