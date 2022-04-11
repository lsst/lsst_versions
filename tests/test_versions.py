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

import os.path
import unittest

try:
    import git
except ImportError:
    git = None

from lsst_versions import find_dev_lsst_version

TESTDIR = os.path.abspath(os.path.dirname(__file__))
GITDIR = os.path.normpath(os.path.join(TESTDIR, os.path.pardir))


@unittest.skipIf(git is None, "GitPython package is not installed.")
class VersionsTestCase(unittest.TestCase):
    """Test Git version finding."""

    def setUp(self):
        try:
            git.Repo(GITDIR)
        except Exception:
            raise unittest.SkipTest("Git repository for this package is not accessible.")

    def test_versions(self):
        """Determine versions of this package."""
        versions = (
            # Effectivelt a no-op until the package has some tags.
            ("53d5d17", "1.0.0a00000000"),
        )

        for tag, expected in versions:
            version = find_dev_lsst_version(GITDIR, tag)
            with self.subTest(tag=tag, expected=expected):
                self.assertEqual(version, expected)


if __name__ == "__main__":
    unittest.main()
